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
#    This module validates a VPN connection from addon settings page.

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
import sys
from libs.common import connectVPN
from libs.utility import debugTrace, errorTrace, infoTrace, getID, getName
from libs.vpnproviders import usesPassAuth, getVPNLocation, getUserDataPath
from libs.vpnplatform import getAddonPath

# Get the first argument which will indicate the connection that's being dealt with
connection_order = int(sys.argv[1])

debugTrace("Entered connect.py with parameter " + str(connection_order))

if not getID() == "":

    addon = xbmcaddon.Addon(getID())
    addon_name = getName()

    # If a new connection is being validated, check everything needed is entered
    vpn_provider = addon.getSetting("vpn_provider")
    vpn_username = addon.getSetting("vpn_username")
    vpn_password = addon.getSetting("vpn_password")
        
    if xbmcvfs.exists(getUserDataPath(getVPNLocation(vpn_provider) + "/DEFAULT.txt")):
        vpn_username = "default"
        vpn_password = "default"
        
    if not usesPassAuth(getVPNLocation(vpn_provider)) or (not vpn_username == "" and not vpn_provider == ""):
        connectVPN(str(connection_order), "")
    else:
        if vpn_provider == "":
            xbmcgui.Dialog().ok(addon_name, "Please select a VPN provider and enter a user name and password.")
        else:
            xbmcgui.Dialog().ok(addon_name, "Please enter a user name and password.  " + vpn_provider + " requires them for authentication.")

    # Finally return to the settings screen if that's where we came from
    if connection_order > 0:
        command = "Addon.OpenSettings(" + getID() + ")"
        xbmc.executebuiltin(command)

else:
    errorTrace("connect.py", "VPN service is not ready")
        
debugTrace("Exit connect.py")
