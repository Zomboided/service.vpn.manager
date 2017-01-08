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
#    This module validates a resets all VPN connections from the VPN
#    Manager for OpenVPN addon settings page.

import xbmcgui
import xbmcaddon
from libs.common import resetVPNConnections, stopService, startService
from libs.utility import debugTrace

debugTrace("-- Entered resetVPN.py --")

# Get info about the addon that this script is pretending to be attached to
addon = xbmcaddon.Addon("service.vpn.manager")
addon_name = addon.getAddonInfo("name")

success = True
# Reset the VPN connection values stored in the settings.xml
if xbmcgui.Dialog().yesno(addon_name, "Updating the VPN settings will reset all VPN connections.  Connections must be re-validated before use.\nContinue?"):
    # Display dialog to show what's going on
    progress = xbmcgui.DialogProgress()
    progress_title = "Resetting VPN connections."
    progress.create(addon_name,progress_title) 

    # Stop the VPN monitor
    xbmc.sleep(100)
    progress.update(0, progress_title, "Pausing VPN monitor.")
    xbmc.sleep(100)
    if not stopService():
        progress.close()
        # Display error result in an ok dialog
        errorTrace("resetVPN.py", "VPN monitor service is not running, can't reset VPNs")
        xbmcgui.Dialog().ok(progress_title, "Error, Service not running. Check log and re-enable.")
        success = False
    
    # Disconnect and reset all connections
    if success:
        progress.update(20, progress_title, "VPN monitor paused.")
        xbmc.sleep(500)
        progress.update(40, progress_title, "Stopping any active VPN connection.")
        xbmc.sleep(100)
        resetVPNConnections(addon)
    
    # Restart the VPN monitor
    if success:
        progress.update(60, progress_title, "VPN connections have been reset.")
        xbmc.sleep(500)
        progress.update(80, progress_title, "Restarting VPN monitor.")
        xbmc.sleep(100)
        if not startService():
            progress.close()
            errorTrace("resetVPN.py", "VPN monitor service is not running, connections have been reset")
            xbmcgui.Dialog().ok(progress_title, "Error, cannot restart service. Check log and re-enable.")
            success = False      
        else:
            # Close out the final progress dialog
            progress.update(100, progress_title, "VPN monitor restarted.")
            xbmc.sleep(500)
            progress.close()

xbmc.executebuiltin("Addon.OpenSettings(service.vpn.manager)")      

debugTrace("-- Exit resetVPN.py --")