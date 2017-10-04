#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#    Copyright (C) 2017 Zomboided
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
#    This module displays a list of connections on the screen and allows a
#    user to select one to connect to.  It can be called from a remote button.

import xbmcgui
import xbmcaddon
from libs.vpnproviders import getAddonList
from libs.common import requestVPNCycle, getFilteredProfileList, getFriendlyProfileList, setAPICommand, connectionValidated, getValidatedList
from libs.common import getVPNProfile, getVPNProfileFriendly, getVPNState, clearVPNCycle, getCycleLock, freeCycleLock
from libs.utility import debugTrace, errorTrace, infoTrace, newPrint

debugTrace("-- Entered table.py --")

addon = xbmcaddon.Addon("service.vpn.manager")
addon_name = addon.getAddonInfo("name")

cancel_text = "[I][COLOR grey]Cancel[/COLOR][/I]"
disconnect_text = "[COLOR red]Disconnect[/COLOR]"
disconnect_text = "[COLOR red]Disconnected[/COLOR]"

# Don't display the table if there's nothing been set up
if connectionValidated(addon):
    if getCycleLock():
        # Want to stop cycling whilst this menu is displayed, and clear any active cycle
        clearVPNCycle()
        if addon.getSetting("table_display_type") == "All Connections":
            # Build a list of all ovpn files using the current active filter
            all_connections = getAddonList(addon.getSetting("vpn_provider_validated"), "*.ovpn")
            ovpn_connections = getFilteredProfileList(all_connections, addon.getSetting("vpn_protocol"), None)
            ovpn_connections.sort()
        else:
            # Build a list of all validated connections
            ovpn_connections = getValidatedList(addon, "")
        # Build the friendly list, displaying any active connection in blue
        location_connections = getFriendlyProfileList(ovpn_connections, getVPNProfile(), "ff0099ff")
        if getVPNState() == "started":
            title = "Connected - " + getVPNProfileFriendly()
            location_connections.insert(0, disconnect_text)
        else:
            title = "Disconnected"
            location_connections.insert(0, disconnected_text)
        
        location_connections.append(cancel_text)

        i = xbmcgui.Dialog().select(title, location_connections)
        if location_connections[i] == disconnect_text or disconnected_text:
            setAPICommand("Disconnect")
        elif not location_connections[i] == cancel_text:
            setAPICommand(ovpn_connections[i-1])
        freeCycleLock()
else:
    xbmcgui.Dialog().notification(addon_name, "VPN is not set up and authenticated.", xbmcgui.NOTIFICATION_ERROR, 10000, True)

debugTrace("-- Exit table.py --")
