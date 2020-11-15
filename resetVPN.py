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
#    This module resets all VPN connections

import xbmcgui
import xbmcaddon
from libs.common import resetVPNConnections, stopService, startService, DIALOG_SPEED, getVPNRequestedProfile, setAPICommand
from libs.utility import debugTrace, errorTrace, infoTrace, newPrint, getID, getName

debugTrace("-- Entered resetVPN.py --")

if not getID() == "":
    # Get info about the addon that this script is pretending to be attached to
    addon = xbmcaddon.Addon(getID())
    addon_name = getName()

    success = True
    # Reset the VPN connection values stored in the settings.xml
    if xbmcgui.Dialog().yesno(addon_name, "Updating the VPN settings will reset all VPN connections.  Connections must be re-validated before use.\nContinue?"):
        # Display dialog to show what's going on
        progress = xbmcgui.DialogProgress()
        progress_title = "Resetting VPN connections"
        progress.create(addon_name,progress_title) 

        if not getVPNRequestedProfile() == "":
            progress.close()
            xbmcgui.Dialog().ok(addon_name, "Connection to VPN being attempted and will be aborted.  Try again in a few seconds.")
            setAPICommand("Disconnect")
            success = False
        
        if success:
            # Stop the VPN monitor
            xbmc.sleep(100)
            progress.update(0, progress_title + "\n" + "Pausing VPN monitor..." + "\n\n")
            xbmc.sleep(100)
                
            if not stopService():
                progress.close()
                # Display error result in an ok dialog
                errorTrace("resetVPN.py", "VPN monitor service is not running, can't reset VPNs")
                xbmcgui.Dialog().ok(progress_title, "Error, Service not running. Check log and re-enable.")
                success = False
        
        # Disconnect and reset all connections
        if success:
            progress.update(20, progress_title + "\n" + "VPN monitor paused" + "\n\n")
            xbmc.sleep(DIALOG_SPEED)
            progress.update(40, progress_title + "\n" + "Stopping any active VPN connection..." + "\n\n")
            xbmc.sleep(100)
            resetVPNConnections(addon)
            # Reset any validated values
            addon.setSetting("vpn_provider_validated", "")
            addon.setSetting("vpn_username_validated", "")
            addon.setSetting("vpn_password_validated", "")
        
        # Restart the VPN monitor
        if success:
            progress.update(60, progress_title + "\n" + "VPN connections have been reset" + "\n\n")
            xbmc.sleep(DIALOG_SPEED)
            progress.update(80, progress_title + "\n" + "Restarting VPN monitor..." + "\n\n")
            xbmc.sleep(100)
            if not startService():
                progress.close()
                errorTrace("resetVPN.py", "VPN monitor service is not running, connections have been reset")
                xbmcgui.Dialog().ok(progress_title, "Error, cannot restart service. Check log and re-enable.")
                success = False      
            else:
                # Close out the final progress dialog
                progress.update(100, progress_title + "\n" + "VPN monitor restarted" + "\n\n")
                xbmc.sleep(DIALOG_SPEED)
                progress.close()
                
    command = "Addon.OpenSettings(" + getID() + ")"
    xbmc.executebuiltin(command)     
else:
    errorTrace("resetVPN.py", "VPN service is not ready")
    
debugTrace("-- Exit resetVPN.py --")