#!/usr/bin/env python
#-*- coding:utf-8 -*-

#  Copyright (C) 2010-2018  CEA/DEN
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

"""
This file is the main entry file to use salomeTools,
in mode Command Line Argument(s) (CLI)
"""

import os
import sys

# exit OKSYS and KOSYS seems equal on linux or windows
OKSYS = 0  # OK
KOSYS = 1  # KO

# get path to salomeTools sources
satdir = os.path.dirname(os.path.realpath(__file__))
srcdir = os.path.join(satdir, 'src')
cmdsdir = os.path.join(satdir, 'commands')

# Make the src & commands package accessible from all code
sys.path.insert(0, satdir)
sys.path.insert(0, srcdir) # TODO remove that
sys.path.insert(0, cmdsdir) # TODO remove that

import src.logger as LOG
import src.debug as DBG # Easy print stderr (for DEBUG only)

logger = LOG.getDefaultLogger()

#################################
# MAIN
#################################
if __name__ == "__main__":
    from src.salomeTools import Sat # it is time to do import

    _debug = False # Have to be False in production (for programmers DEBUG only)
    DBG.push_debug(_debug) # as __main__ with sys.exit so no need pop_debug

    args = sys.argv[1:] # skip useless "sat'
    sat = Sat(logger) # instantiate the salomeTools class

    try:
      returnCode = sat.execute_cli(args)
    except Exception as e:
      # error as may be unknown problem
      # verbose debug message with traceback if developers
      msg = "Exception raised for execute_cli('%s'):\n" % " ".join(args)
      logger.critical(DBG.format_exception(msg))
      logger.close() # important to close logger
      sys.exit(KOSYS)

    # no Exception but may be known problem
    DBG.write("execute_cli return code", returnCode)
    if returnCode.isOk():
      # OK no trace
      logger.step("sat exit code: %s" % returnCode)
    else:
      # KO warning as known problem have to say why
      logger.warning("sat exit code: %s" % returnCode)
    logger.close() # important to close logger
    sys.exit(returnCode.toSys())


else:
    logger.critical("forbidden/unexpected mode for __name__ '%s'" % __name__)
    logger.close() # important to close logger
    sys.exit(KOSYS)



