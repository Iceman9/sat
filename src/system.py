#!/usr/bin/env python
#-*- coding:utf-8 -*-
#  Copyright (C) 2010-2013  CEA/DEN
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 2.1 of the License.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307 USA

'''
In this file : all functions that do a system call, 
like open a browser or an editor, or call a git command
'''

import os
import subprocess as SP
import time
import tarfile
import zipfile
import time
 

import debug as DBG
import utilsSat as UTS
import src

from . import printcolors

def show_in_editor(editor, filePath, logger):
    '''open filePath using editor.
    
    :param editor str: The editor to use.
    :param filePath str: The path to the file to open.
    '''
    # default editor is vi
    if editor is None or len(editor) == 0:
        editor = 'vi'
    
    if '%s' not in editor:
        editor += ' %s'

    try:
        # launch cmd using subprocess.Popen
        cmd = editor % filePath
        logger.write('Launched command:\n' + cmd + '\n', 5)
        p = SP.Popen(cmd, shell=True)
        p.communicate()
    except Exception:
        logger.write(printcolors.printcError(_("Unable to edit file %s\n") 
                                             % filePath), 1)

def show_in_webbrowser(editor, filePath, logger):
    '''open filePath using web browser firefox, chromium etc...
    if file is xml, previous http sever is done before to fix new security problems
    
    :param editor str: The web browser to use.
    :param filePath str: The path to the file to open.
    '''
    import psutil
    # default editor is firefox
    if editor is None or len(editor) == 0:
        editor = 'firefox'
    
    path, namefile = os.path.split(filePath)
    basefile, ext = os.path.splitext(namefile)

    # previouly http.server 8765/6/7... kill ... or not ? TODO wait and see REX
    port = os.getenv('SAT_PORT_LOG', '8765')
    for proc in psutil.process_iter():
      # help(proc)
      cmdline = " ".join(proc.cmdline())
      if "python3 -m http.server %s" % port in cmdline:
        print("kill previous process '%s'" % cmdline)
        proc.kill()  # TODO may be not owner ? -> change 8766/7/8... as SAT_PORT_LOG
        
    cmd = """
set -x
cd %(path)s
python3 -m http.server %(port)s &> /dev/null &
%(editor)s http://localhost:%(port)s/%(namefile)s
""" % {"path": path, "editor": editor, "namefile": namefile, 'port': port}

    # print("show_in_webbrowser:\n%s" % cmd)
    
    try:
        # launch cmd using subprocess.Popen
        logger.write('Launched command:\n%s\n' % cmd, 5)
        p = SP.Popen(cmd, shell=True, stdout=SP.PIPE, stderr=SP.STDOUT)
        res_out, _ = p.communicate()   # _ = None as stderr=SP.STDOUT
        # print("Launched command stdout:\n%s" % res_out)
    except Exception as e:
        logger.write(printcolors.printcError(_("Unable to display file %s\n%s\n") 
                                             % (filePath, e)), 1)
    

def git_describe(repo_path):
    '''Use git describe --tags command to return tag description of the git repository"
    :param repo_path str: The git repository to describe
    '''
    git_cmd="cd %s;git describe --tags" % repo_path
    p = SP.Popen(git_cmd, shell=True, stdin=SP.PIPE, stdout=SP.PIPE, stderr=SP.PIPE)
    p.wait()
    if p.returncode != 0:
        return False
    else:
        tag_description=p.stdout.readlines()[0].strip()
        # with python3 this utf8 bytes should be decoded
        if isinstance(tag_description, bytes):
            tag_description=tag_description.decode("utf-8", "ignore")
        return tag_description

def git_extract(from_what, tag, git_options, git_commands, where, logger, environment=None):
  '''Extracts sources from a git repository.
87
  :param from_what str: The remote git repository.
  :param tag str: The tag.
  :param git_options str: git options
  :param git_commands array: git command lines
  :param where str: The path where to extract.
  :param logger Logger: The logger instance to use.
  :param environment src.environment.Environ: The environment to source when extracting.
  :return: True if the extraction is successful
  :rtype: boolean
  '''
  DBG.write("git_extract", [from_what, tag, str(where)])
  if not where.exists():
    where.make()
  where_git = os.path.join(str(where), ".git")
  if tag == "master" or tag == "HEAD":
    if src.architecture.is_windows():
      cmd = "git clone %(git_options)s %(remote)s %(where)s"
      if len(git_commands) > 0:
        cmd+= "&&" + "cd %(where)s"
        for git_command in git_commands:
          cmd+= "&&" + git_command
    else:
      cmd = "\n" + "set -x"
      cmd+= "\n" + "git clone %(git_options)s %(remote)s %(where)s"
      cmd+= "\n" + "if [ $? -ne 0 ]; then"
      cmd+= "\n" + "  exit 1"
      cmd+= "\n" + "fi"
      cmd+= "\n" + "cd %(where)s"
      cmd+= "\n" + "git submodule update --init"
      cmd+= "\n" + "if [ $? -ne 0 ]; then"
      cmd+= "\n" + "  exit 1"
      cmd+= "\n" + "fi"
      cmd+= "\n" + "cd -"
      cmd+= "\n" + "touch -d \"$(git --git-dir=%(where_git)s  log -1 --format=date_format)\" %(where)s"
      cmd+= "\n" + "if [ $? -ne 0 ]; then"
      cmd+= "\n" + "  exit 1"
      cmd+= "\n" + "fi"
      if len(git_commands) > 0:
        cmd+= "\n" + "cd %(where)s"
        for git_command in git_commands:
            cmd+= "\n" + git_command
            cmd+= "\n" + "if [ $? -ne 0 ]; then"
            cmd+= "\n" + "  exit 1"
            cmd+= "\n" + "fi"
  else:
    if src.architecture.is_windows():
      cmd = "rmdir /S /Q %(where)s"
      cmd+= "&&" + "git clone %(git_options)s %(remote)s %(where)s"
      cmd+= "&&" + "git --git-dir=%(where_git)s --work-tree=%(where)s checkout %(tag)s"
      if len(git_commands) > 0:
        cmd+= "&&" + "cd %(where)s"
        for git_command in git_commands:
          cmd+= "&&" + git_command
    else:
      cmd = "\n" + "set -x"
      cmd+= "\n" + "git clone %(git_options)s %(remote)s %(where)s"
      cmd+= "\n" + "if [ $? -ne 0 ]; then"
      cmd+= "\n" + "  exit 1"
      cmd+= "\n" + "fi"
      cmd+= "\n" + "git --git-dir=%(where_git)s --work-tree=%(where)s checkout %(tag)s"
      cmd+= "\n" + "if [ $? -ne 0 ]; then"
      cmd+= "\n" + "  exit 1"
      cmd+= "\n" + "fi"
      cmd+= "\n" + "cd %(where)s"
      cmd+= "\n" + "git submodule update --init"
      cmd+= "\n" + "if [ $? -ne 0 ]; then"
      cmd+= "\n" + "  exit 1"
      cmd+= "\n" + "fi"
      cmd+= "\n" + "cd -"
      if len(git_commands) > 0:
        cmd+= "\n" + "cd %(where)s"
        for git_command in git_commands:
            cmd+= "\n" + git_command
            cmd+= "\n" + "if [ $? -ne 0 ]; then"
            cmd+= "\n" + "  exit 1"
            cmd+= "\n" + "fi"
      cmd+= "\n" + "git --git-dir=%(where_git)s status | grep HEAD"
      cmd+= "\n" + "touch -d \"$(git --git-dir=%(where_git)s  log -1 --format=date_format)\" %(where)s"
      cmd+= "\n" + "exit 0"
  aDict = {'%(git_options)s': git_options,
           '%(remote)s'   : from_what,
           '%(where)s'    : str(where),
           '%(tag)s'      : tag,
           '%(where_git)s': where_git
           }
  for k, v in aDict.items():
      cmd= cmd.replace(k,v)
  cmd=cmd.replace('date_format', '"%ai"')
  logger.logTxtFile.write("\n" + cmd + "\n")
  logger.logTxtFile.flush()
  DBG.write("cmd", cmd)
  # git commands may fail sometimes for various raisons 
  # (big module, network troubles, tuleap maintenance)
  # therefore we give several tries
  i_try = 0
  max_number_of_tries = 3
  sleep_delay = 30  # seconds
  while (True):
    i_try += 1
    rc = UTS.Popen(cmd, cwd=str(where.dir()), env=environment.environ.environ, logger=logger)
    if rc.isOk() or (i_try>=max_number_of_tries):
      break
    logger.write('\ngit command failed! Wait %d seconds and give an other try (%d/%d)\n' % \
                 (sleep_delay, i_try + 1, max_number_of_tries), 3)
    time.sleep(sleep_delay) # wait a little

  return rc.isOk()


def git_extract_sub_dir(from_what, tag, git_options, git_commands, where, sub_dir, logger, environment=None):
  '''Extracts sources from a subtree sub_dir of a git repository.

  :param from_what str: The remote git repository.
  :param tag str: The tag.
  :param git_options str: git options
  :param git_commands array: git command lines
  :param where str: The path where to extract.
  :param sub_dir str: The relative path of subtree to extract.
  :param logger Logger: The logger instance to use.
  :param environment src.environment.Environ: The environment to source when extracting.
  :return: True if the extraction is successful
  :rtype: boolean
  '''
  strWhere = str(where)
  tmpWhere = strWhere + '_tmp'
  parentWhere = os.path.dirname(strWhere)
  if not os.path.exists(parentWhere):
    logger.error("not existing directory: %s" % parentWhere)
    return False
  if os.path.isdir(strWhere):
    logger.error("do not override existing directory: %s" % strWhere)
    return False
  aDict = {'%(git_options)s': git_options,
           '%(remote)s'     : from_what,
           '%(tag)s'        : tag,
           '%(sub_dir)s'    : sub_dir,
           '%(where)s'      : strWhere,
           '%(parentWhere)s': parentWhere,
           '%(tmpWhere)s'   : tmpWhere
           }
  DBG.write("git_extract_sub_dir", aDict)
  if not src.architecture.is_windows():
    cmd = "\n" + "set -x"
    cmd+= "\n" + "export tmpDir=%(tmpWhere)s"
    cmd+= "\n" + "rm -rf $tmpDir"
    cmd+= "\n" + "git clone %(git_options)s %(remote)s $tmpDir"
    cmd+= "\n" + "if [ $? -ne 0 ]; then"
    cmd+= "\n" + "  exit 1"
    cmd+= "\n" + "fi"
    cmd+= "\n" + "cd $tmpDir"
    cmd+= "\n" + "git checkout %(tag)s"
    cmd+= "\n" + "if [ $? -ne 0 ]; then"
    cmd+= "\n" + "  exit 1"
    cmd+= "\n" + "fi"
    if len(git_commands) > 0:
      for git_command in git_commands:
        cmd+= "\n" + git_command
        cmd+= "\n" + "if [ $? -ne 0 ]; then"
        cmd+= "\n" + "  exit 1"
        cmd+= "\n" + "fi"
    cmd+= "\n" + "mv %(sub_dir)s %(where)s"
    cmd+= "\n" + "git log -1 > %(where)s/README_git_log.txt"
    cmd+= "\n" + "if [ $? -ne 0 ]; then"
    cmd+= "\n" + "  exit 1"
    cmd+= "\n" + "fi"
    cmd+= "\n" + "rm -rf ${tmpDir}"
  else:
    cmd+=        "set tmpDir=%(tmpWhere)s"
    cmd+= "&&" + "rmdir /S /Q %tmpDir%"
    cmd+= "&&" + "git clone %(git_options)s %(remote)s %tmpDir%"
    cmd+= "&&" + "cd %tmpDir%"
    cmd+= "&&" + "git checkout %(tag)s"
    if len(git_commands) > 0:
      for git_command in git_commands:
        cmd+= "&&" + git_command
    cmd+= "&&" + "mv %(sub_dir)s %(where)s"
    cmd+= "&&" + "git log -1 > %(where)s\\README_git_log.txt"
    cmd+= "&&" + "rmdir /S /Q %tmpDir%"

  for k, v in aDict.items():
      cmd= cmd.replace(k,v)
  DBG.write("cmd", cmd)

  for nbtry in range(0,3): # retries case of network problem
    rc = UTS.Popen(cmd, cwd=parentWhere, env=environment.environ.environ, logger=logger)
    if rc.isOk(): break
    time.sleep(30) # wait a little

  return rc.isOk()

def archive_extract(from_what, where, logger, backup_prefix=""):
    '''Extracts sources from an archive.
    
    :param from_what str: The path to the archive.
    :param where str: The path where to extract.
    :param logger Logger: The logger instance to use.
    :param backup_prefix str: Additional prefix to the path. In case we wish a
        different root name of the archive
    :return: True if the extraction is successful
    :rtype: boolean
    '''
    try:
        lower = from_what.lower()

        tar_extracts = ['tar.gz', 'tgz', 'tar.bz2', 'tar.xz']
        if any([lower.endswith(_) for _ in tar_extracts]):
            # First see if the files in the archive have a common prefix
            archive = tarfile.open(from_what)
            members = archive.getnames()
            common_prefix = os.path.commonprefix(members)
            if len(common_prefix) == 0:
                # No root directory.
                where = os.path.join(str(where), backup_prefix)
                common_prefix = backup_prefix

            archive.extractall(path=str(where))
            # for i in members:
                # archive.extract(i, path=str(where))
        elif lower.endswith("zip"):
            with zipfile.ZipFile(from_what, "r") as zip_f:
                common_prefix = os.path.commonprefix(zip_f.namelist())
                if len(common_prefix) == 0:
                    # No root directory.
                    where = os.path.join(str(where), backup_prefix)
                    common_prefix = backup_prefix
                zip_f.extractall(str(where))
        else:
            raise Exception("Failed to extract")

        return True, common_prefix
    except Exception as exc:
        logger.write("archive_extract: %s\n" % exc)
        return False, None

def cvs_extract(protocol, user, server, base, tag, product, where,
                logger, checkout=False, environment=None):
    '''Extracts sources from a cvs repository.
    
    :param protocol str: The cvs protocol.
    :param user str: The user to be used.
    :param server str: The remote cvs server.
    :param base str: .
    :param tag str: The tag.
    :param product str: The product.
    :param where str: The path where to extract.
    :param logger Logger: The logger instance to use.
    :param checkout boolean: If true use checkout cvs.
    :param environment src.environment.Environ: The environment to source when
                                                extracting.
    :return: True if the extraction is successful
    :rtype: boolean
    '''

    opttag = ''
    if tag is not None and len(tag) > 0:
        opttag = '-r ' + tag

    cmd = 'export'
    if checkout:
        cmd = 'checkout'
    elif len(opttag) == 0:
        opttag = '-DNOW'
    
    if len(protocol) > 0:
        root = "%s@%s:%s" % (user, server, base)
        command = "cvs -d :%(protocol)s:%(root)s %(command)s -d %(where)s %(tag)s %(product)s" % \
            { 'protocol': protocol, 'root': root, 'where': str(where.base()),
              'tag': opttag, 'product': product, 'command': cmd }
    else:
        command = "cvs -d %(root)s %(command)s -d %(where)s %(tag)s %(base)s/%(product)s" % \
            { 'root': server, 'base': base, 'where': str(where.base()),
              'tag': opttag, 'product': product, 'command': cmd }

    logger.write(command + "\n", 5)

    if not where.dir().exists():
        where.dir().make()

    logger.logTxtFile.write("\n" + command + "\n")
    logger.logTxtFile.flush()        
    res = SP.call(command, cwd=str(where.dir()),
                           env=environment.environ.environ,
                           shell=True,
                           stdout=logger.logTxtFile,
                           stderr=SP.STDOUT)
    return (res == 0)

def svn_extract(user,
                from_what,
                tag,
                where,
                logger,
                checkout=False,
                environment=None):
    '''Extracts sources from a svn repository.
    
    :param user str: The user to be used.
    :param from_what str: The remote git repository.
    :param tag str: The tag.
    :param where str: The path where to extract.
    :param logger Logger: The logger instance to use.
    :param checkout boolean: If true use checkout svn.
    :param environment src.environment.Environ: The environment to source when
                                                extracting.
    :return: True if the extraction is successful
    :rtype: boolean
    '''
    if not where.exists():
        where.make()

    if checkout:
        command = "svn checkout --username %(user)s %(remote)s %(where)s" % \
            { 'remote': from_what, 'user' : user, 'where': str(where) }
    else:
        command = ""
        if os.path.exists(str(where)):
            command = "/bin/rm -rf %(where)s && " % \
                { 'remote': from_what, 'where': str(where) }
        
        if tag == "master":
            command += "svn export --username %(user)s %(remote)s %(where)s" % \
                { 'remote': from_what, 'user' : user, 'where': str(where) }       
        else:
            command += "svn export -r %(tag)s --username %(user)s %(remote)s %(where)s" % \
                { 'tag' : tag, 'remote': from_what, 'user' : user, 'where': str(where) }
    
    logger.logTxtFile.write(command + "\n")
    
    logger.write(command + "\n", 5)
    logger.logTxtFile.write("\n" + command + "\n")
    logger.logTxtFile.flush()
    res = SP.call(command, cwd=str(where.dir()),
                           env=environment.environ.environ,
                           shell=True,
                           stdout=logger.logTxtFile,
                           stderr=SP.STDOUT)
    return (res == 0)

def get_pkg_check_cmd(dist_name):
    '''Build the command to use for checking if a linux package is installed or not.'''

    if dist_name in ["CO","FD","MG","MD","CO","OS"]: # linux using rpm
        linux="RH"  
        manager_msg_err="Error : command failed because sat was not able to find rpm command"
    else:
        linux="DB"
        manager_msg_err="Error : command failed because sat was not able to find apt command"

    # 1- search for an installed package manager (rpm on rh, apt or dpkg-query on db)
    cmd_which_rpm  = ["which", "rpm"]
    cmd_which_apt  = ["which", "apt"]
    cmd_which_dpkg = ["which", "dpkg-query"]
    with open(os.devnull, 'w') as devnull:
        # 1) we search for apt (debian based systems)
        completed=SP.call(cmd_which_dpkg,stdout=devnull, stderr=SP.STDOUT)
        if completed==0 and linux=="DB":
            cmd_is_package_installed = ["dpkg-query", "-l"]
        else:
            # 2) if dpkg not found search for apt
            completed = SP.call(cmd_which_apt, stdout=devnull, stderr=SP.STDOUT)
            if completed == 0 and linux == "DB":
                cmd_is_package_installed = ["apt", "list", "--installed"]
            else:
                # 3) if apt not found search for rpm (redhat)
                completed=SP.call(cmd_which_rpm,stdout=devnull, stderr=SP.STDOUT) # only 3.8! ,capture_output=True)
                if completed==0 and linux=="RH":
                    cmd_is_package_installed=["rpm", "-q"]
                else:
                    # no package manager was found corresponding to dist_name
                    raise src.SatException(manager_msg_err)
    return cmd_is_package_installed

def check_system_pkg(check_cmd,pkg):
    '''Check if a package is installed
    :param check_cmd list: the list of command to use system package manager
    :param user str: the pkg name to check
    :rtype: str
    :return: a string with package name with status un message
    '''
    # build command
    FNULL = open(os.devnull, 'w')
    cmd_is_package_installed=[]
    for cmd in check_cmd:
        cmd_is_package_installed.append(cmd)
    cmd_is_package_installed.append(pkg)


    if check_cmd[0]=="apt":
        # special treatment for apt
        # apt output is too messy for being used
        # some debian packages have version numbers in their name, we need to add a *
        # also apt do not return status, we need to use grep
        # and apt output is too messy for being used 
        cmd_is_package_installed[-1]+="*" # we don't specify in pyconf the exact name because of version numbers
        p=SP.Popen(cmd_is_package_installed, stdout=SP.PIPE, stderr=FNULL)
        try:
            output = SP.check_output(['grep', pkg], stdin=p.stdout)
            msg_status=src.printcolors.printcSuccess("OK")
        except Exception:
            msg_status=src.printcolors.printcError("KO")
            msg_status+=" (package is not installed!)\n"
    elif check_cmd[0] == "dpkg-query":
        # special treatment for dpkg-query
        # some debian packages have version numbers in their name, we need to add a *
        # also dpkg-query do not return status, we need to use grep
        # and dpkg-query output is too messy for being used
        cmd_is_package_installed[-1] = (
            cmd_is_package_installed[-1] + "*"
        )  # we don't specify in pyconf the exact name because of version numbers
        p = SP.Popen(cmd_is_package_installed, stdout=SP.PIPE, stderr=FNULL)
        try:
            output = SP.check_output(["grep", "-E", "^[ii|ri]"], stdin=p.stdout)
            msg_status = src.printcolors.printcSuccess("OK")
        except SP.CalledProcessError:
            msg_status = src.printcolors.printcError("KO")
            msg_status += " (package is not installed!)\n"
    else:
        p=SP.Popen(cmd_is_package_installed, stdout=SP.PIPE, stderr=FNULL, env={})
        output, err = p.communicate()
        rc = p.returncode
        if rc==0:
            msg_status=src.printcolors.printcSuccess("OK")
            # in python3 output is a byte and should be decoded
            if isinstance(output, bytes):
                output = output.decode("utf-8", "ignore")
            msg_status+=" (" + output.replace('\n',' ') + ")\n" # remove output trailing \n
        else:
            msg_status=src.printcolors.printcError("KO")
            msg_status+=" (package is not installed!)\n"

    return msg_status
