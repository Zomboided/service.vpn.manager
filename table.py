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
from libs.vpnproviders import getAddonList, isAlternative, getAlternativeLocations, getAlternativeLocationName
from libs.common import requestVPNCycle, getFilteredProfileList, getFriendlyProfileList, setAPICommand, connectionValidated, getValidatedList
from libs.common import getVPNProfile, getVPNProfileFriendly, getVPNState, clearVPNCycle, getCycleLock, freeCycleLock
from libs.utility import debugTrace, errorTrace, infoTrace, newPrint, getID, getName

debugTrace("-- Entered table.py --")

if not getID() == "":
    # Get info about the addon that this script is pretending to be attached to
    addon = xbmcaddon.Addon(getID())
    addon_name = getName()

    cancel_text = "[I][COLOR grey]Cancel[/COLOR][/I]"
    disconnect_text = "[COLOR ffff0000]Disconnect[/COLOR]"
    disconnected_text = "[COLOR ffff0000](Disconnected)[/COLOR]"

    # Don't display the table if there's nothing been set up
    if connectionValidated(addon):
        if getCycleLock():
        
            vpn_provider = addon.getSetting("vpn_provider_validated")
        
            # Want to stop cycling whilst this menu is displayed, and clear any active cycle
            clearVPNCycle()
            if addon.getSetting("table_display_type") == "All connections":
                # Build a list of all ovpn files using the current active filter
                if not isAlternative(vpn_provider):
                    all_connections = getAddonList(addon.getSetting("vpn_provider_validated"), "*.ovpn")
                    location_connections = getFilteredProfileList(all_connections, addon.getSetting("vpn_protocol"), None)
                    location_connections.sort()
                else:
                    location_connections = getAlternativeLocations(vpn_provider, False)
            else:
                # Build a list of all validated connections
                location_connections = getValidatedList(addon, "")
            # Build the friendly list, displaying any active connection in blue
            connections = getFriendlyProfileList(location_connections, getVPNProfile(), "ff00ff00")
            if getVPNState() == "started":
                title = "Connected - " + getVPNProfileFriendly()
                connections.insert(0, disconnect_text)
            else:
                title = "Disconnected"
                connections.insert(0, disconnected_text)
            
            connections.append(cancel_text)

            i = xbmcgui.Dialog().select(title, connections)
            if connections[i] == disconnect_text or connections[i] == disconnected_text:
                setAPICommand("Disconnect")
            elif not connections[i] == cancel_text:
                if getVPNProfile() == location_connections[i-1] and (isAlternative(vpn_provider) or addon.getSetting("allow_cycle_reconnect") == "true"):
                    setAPICommand("Reconnect")
                else:
                    if isAlternative(vpn_provider):
                        connection = getAlternativeLocationName(vpn_provider, connections[i])
                        if connection == "":
                            errorTrace("table.py", "Could not find a location for the selected item " + connection[i])
                    else:
                        connection = location_connections[i-1]
                    if not connection == "":
                        setAPICommand(connection)
            freeCycleLock()
    else:
        xbmcgui.Dialog().notification(addon_name, "VPN is not set up and authenticated.", xbmcgui.NOTIFICATION_ERROR, 10000, True)
else:
    errorTrace("table.py", "VPN service is not ready")
    
debugTrace("-- Exit table.py --")
