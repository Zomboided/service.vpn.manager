#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#    Copyright (C) 2016 Zomboided
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
#    This module allows some limited interaction with the service via
#    a set of commands

import xbmcaddon
import xbmcvfs
import string
from libs.common import setAPICommand, clearAPICommand, getAPICommand
from libs.utility import debugTrace, errorTrace, infoTrace, newPrint

addon = xbmcaddon.Addon("service.vpn.manager")
addon_name = addon.getAddonInfo("name")

# Get the first argument which will indicate the connection that's being dealt with
command = sys.argv[1]
lcommand = command.lower()

debugTrace("Entered api.py with parameter " + command)

if lcommand == "disconnect": 
    setAPICommand("Disconnect")
elif lcommand == "cycle":
    setAPICommand("Cycle")
elif lcommand == "fake":
    setAPICommand("Fake")
elif lcommand == "real":
    setAPICommand("Real")
elif lcommand == "pause":
    setAPICommand("Pause")
elif lcommand == "restart":
    setAPICommand("Restart")
elif lcommand.startswith("connect"): 
    connection = command[8:].strip(' \t\n\r')
    if connection.isdigit():
        c = int(connection)
        # Adjust the 11 below to change conn_max
        if c > 0 and c < 11:
            connection = addon.getSetting(str(c) + "_vpn_validated")
            if not connection == "":
                setAPICommand(connection)
            else:
                errorTrace("api.py", "Connection requested, " + str(c) + " has not been validated")
        else:
            errorTrace("api.py", "Invalid connection, " + str(c) + " requested")
    else:
        if xbmcvfs.exists(connection):
            setAPICommand(connection)
        else:
            errorTrace("api.py", "Requested connection, " + connection + " does not exist")
else:
    errorTrace("api.py", "Unrecognised command: " + command)
    
debugTrace("-- Exit api.py --")
