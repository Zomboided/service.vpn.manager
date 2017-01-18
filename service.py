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
#    Service module for VPN Manager for OpenVPN addon

import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import os
import time
import urllib2
import re
import string
from libs.common import updateServiceRequested, ackUpdate, getVPNProfile, setVPNProfile, getVPNProfileFriendly, setVPNProfileFriendly
from libs.common import getVPNRequestedProfile, setVPNRequestedProfile, getVPNRequestedProfileFriendly, setVPNRequestedProfileFriendly, getIPInfo
from libs.common import setVPNState, getVPNState, stopRequested, ackStop, startRequested, ackStart, updateService, stopVPNConnection, startVPNConnection
from libs.common import getVPNLastConnectedProfile, setVPNLastConnectedProfile, getVPNLastConnectedProfileFriendly, setVPNLastConnectedProfileFriendly
from libs.common import getVPNCycle, clearVPNCycle, writeCredentials, getCredentialsPath, getFriendlyProfileName, isVPNMonitorRunning, setVPNMonitorState
from libs.common import getConnectionErrorCount, setConnectionErrorCount, getAddonPath, isVPNConnected, resetVPNConfig, forceCycleLock, freeCycleLock
from libs.common import getAPICommand, clearAPICommand
from libs.platform import getPlatform, connection_status, getAddonPath, writeVPNLog, supportSystemd, addSystemd, removeSystemd, copySystemdFiles, isVPNTaskRunning
from libs.utility import debugTrace, errorTrace, infoTrace, ifDebug, newPrint
from libs.vpnproviders import removeGeneratedFiles, cleanPassFiles, fixOVPNFiles, getVPNLocation, usesPassAuth, clearKeysAndCerts

debugTrace("-- Entered service.py --")

# Window property constants
last_addon = 'VPN_Manager_Last_Addon'

# Filtered addons
filtered_addons = []

# Lists of primary VPNs and their friendly names (so we don't have to keep pattern matching it)
primary_vpns = []
primary_vpns_friendly = []

# Set the addon name for use in the dialogs
addon = xbmcaddon.Addon()
addon_name = addon.getAddonInfo('name')

accepting_changes = False


def refreshAddonFilterLists():
    # Fetch the list of excluded or filtered addons
    del filtered_addons[:]
    # # Adjust 11 below if changing number of conn_max
    for i in range (0, 11):
        filtered_string = ""
        if i == 0 : filtered_string = addon.getSetting("vpn_excluded_addons")
        else : filtered_string = addon.getSetting(str(i)+"_vpn_addons")
        if not filtered_string == "" : filtered_addons.append(filtered_string.split(","))
        else : filtered_addons.append(None)   
    return

        
def isAddonFiltered(path, current):
    # Return 0 if given addon is excluded, 1 to 10 if it needs a particular VPN or -1 if not found
    # If we're already connected to a primary VPN and the add-on appears multiple times then 
    # return the current connected VPN if it matches, otherwise return the first.  If there
    # are duplicate entries, disconnect will always win.
    
    # Filter out local sources (files) being passed in and return not found
    if not ("://" in path): return -1
    # Strip out the leading 'plugin://' or 'addons://' string, and anything trailing the plugin name
    found = -1
    filtered_addon_path = path[path.index("://")+3:]
    if "/" in filtered_addon_path:
        filtered_addon_path = filtered_addon_path[:filtered_addon_path.index("/")]
    if filtered_addon_path == "": return -1
    # # Adjust 11 below if changing number of conn_max
    for i in range (0, 11):
        if not filtered_addons[i] == None:
            for filtered_string in filtered_addons[i]: 
                if filtered_addon_path == filtered_string:
                    if found == -1 : found = i
                    if i > 0 and i == current : found = i
    return found
        
   
def refreshPrimaryVPNs():
    # Fetch the list of excluded or filtered addons

    del primary_vpns[:]
    del primary_vpns_friendly[:]
    
    # # Adjust 11 below if changing number of conn_max
    for i in range (1, 11):
        primary_vpns.append(addon.getSetting(str(i)+"_vpn_validated"))
        primary_vpns_friendly.append(addon.getSetting(str(i)+"_vpn_validated_friendly"))
    return

    
def refreshPlatformInfo():
    # Write the platform so that options only appear in the settings menu when relevant
    if not addon.getSetting("platform") == str(getPlatform()): addon.setSetting("platform", str(getPlatform()))
    
    # Determine if systemd is available so that extra options appear in the settings menu
    curr_sysd = addon.getSetting("show_preboot_connect")
    if supportSystemd():
        new_sysd = "true"
    else:
        new_sysd = "false"
    if not curr_sysd == new_sysd: addon.setSetting("show_preboot_connect", new_sysd)
    

def checkConnections():
    # Check that all of the connections exist
    # Adjust 11 below if changing number of conn_max
    for i in range (1, 11):        
        next_conn = (addon.getSetting(str(i)+"_vpn_validated"))
        if not next_conn == "" and not xbmcvfs.exists(next_conn):
            return False
    return True
    
def setReboot(property):
    xbmcgui.Window(10000).setProperty("vpn_mgr_reboot", property)

    
def getReboot():
    return xbmcgui.Window(10000).getProperty("vpn_mgr_reboot")


# Given hh:mm, return the number of seconds into a day this represents
def getSeconds(hour_min):
    return int(hour_min[0:2])*3600 + int(hour_min[3:5])*60
    

# Monitor class which will get called when the settings change    
class KodiMonitor(xbmc.Monitor):

    # This gets called every time a setting is changed either programmatically or via the settings dialog.
    # We do our best to ignore settings changing as part of common processes so that we don't do too much
    # work refreshing things, but there are a few calls that will happen anyway (and better to do this)
    # than to miss out on an update that a user makes via the GUI.
    def onSettingsChanged( self ):
        if accepting_changes:
            debugTrace("Requested update to service process via settings monitor")
            updateService("KodiMonitor")


# Player class which will be called when the playback state changes           
#class KodiPlayer(xbmc.Player):
#    def __init__ (self):
#        xbmc.Player.__init__(self)
#        self.logger = None
#
#    def onPlayBackStarted(self, *arg):
#        newPrint("Playback started " + self.getPlayingFile())

        
if __name__ == '__main__':   

    # Initialise some variables we'll be using repeatedly
    monitor = xbmc.Monitor()
    player = xbmc.Player() 
    addon = xbmcaddon.Addon()
    
    # Create a monitor to look out for settings changes
    settingsMonitor = KodiMonitor()
    #playerMonitor = KodiPlayer()
    
    if not xbmcvfs.exists(getAddonPath(True, "connect.py")):
        xbmcgui.Dialog().ok(addon_name, "You've installed VPN Manager incorrectly and the add-on won't work.  Check the log, install a Github released build or install from the repository")
        errorTrace("service.py", "Install is in the wrong place, expecting to find the add-on installed in " + getAddonPath(True,""))
    
    # See if this is a new install...we might want to do things here
    if xbmcvfs.exists(getAddonPath(True, "INSTALL.txt")):
        xbmcvfs.delete(getAddonPath(True, "INSTALL.txt"))
        # This is just wiping out the old way of using pre-generated ovpn files before
        # moving to the brave new world of generating them when they're needed
        stored_version = addon.getSetting("version_number").strip()
        if stored_version == "":
            infoTrace("service.py", "New install, resetting the world " + addon.getSetting("version_number"))
            cleanPassFiles()
            removeGeneratedFiles()
            resetVPNConfig(addon, 1)
            xbmcgui.Dialog().ok(addon_name, "VPN Manager installed.\nPlease set up a VPN provider and then validate a connection")
            xbmc.executebuiltin("Addon.OpenSettings(service.vpn.manager)")
        else:
            # Do a bunch of version number dependent tests
            last_version = int(stored_version.replace(".", ""))
            # This fixes a problem with the 2.2 version that causes the profiles to be regenerated
            if last_version == 22: last_version = 220
            # VPN Unlimited and PureVPN template files were fixed in 1.6.0 so force a reconnect
            if addon.getSetting("vpn_provider_validated") == "VPN Unlimited" and last_version < 160:
                addon.setSetting("1_vpn_validated", "reset")
            if addon.getSetting("vpn_provider_validated") == "PureVPN" and last_version < 160:
                addon.setSetting("1_vpn_validated", "reset")
            # PIA changed in 1.5.0 to offer different connection options so need the user to decide which one to use and reconnect
            if addon.getSetting("vpn_provider_validated") == "Private Internet Access" and last_version < 150:
                addon.setSetting("1_vpn_validated", "reset")
            # Lime changed in 1.9.0 to go from template to separate ovpn files
            if addon.getSetting("vpn_provider_validated") == "LimeVPN" and last_version < 190:
                addon.setSetting("1_vpn_validated", "reset")
            if addon.getSetting("vpn_provider_validated") == "HideIPVPN" and last_version < 191:
                addon.setSetting("1_vpn_validated", "reset")
            # HMA got a cert change in 2.0.2
            if addon.getSetting("vpn_provider_validated") == "HMA" and last_version < 203:
                addon.setSetting("1_vpn_validated", "reset")                
                clearKeysAndCerts("HMA")
            if addon.getSetting("vpn_provider_validated") == "IVPN" and last_version < 210:
                addon.setSetting("1_vpn_validated", "reset")
            # VPN Unlim went from being single key to multiple keys in 2.3.1
            if addon.getSetting("vpn_provider_validated") == "VPNUnlimited" and last_version < 240:
                addon.setSetting("1_vpn_validated", "reset")
                addon.setSetting("user_def_keys", "None")
                clearKeysAndCerts("VPNUnlimited")
            # VyprVPN added encryption levels in 2.4.2 and fiddled with some of the names
            if addon.getSetting("vpn_provider_validated") == "VyprVPN" and last_version < 242:
                addon.setSetting("1_vpn_validated", "reset")
                
    addon.setSetting("version_number", addon.getAddonInfo("version"))
   
    # If the addon was running happily previously (like before an uninstall/reinstall or update)
    # then regenerate the OVPNs for the validated provider.
    primary_path = addon.getSetting("1_vpn_validated")

    if not primary_path == "" and not xbmcvfs.exists(primary_path):
        infoTrace("service.py", "New install, but was using good VPN previously.  Regenerate OVPNs")
        if not fixOVPNFiles(getVPNLocation(addon.getSetting("vpn_provider_validated")), addon.getSetting("vpn_locations_list")) or not checkConnections():
            xbmcgui.Dialog().ok(addon_name, "One of the VPN connections you were using previously is no longer available.  Please re-validate all connections.") 
            cleanPassFiles()
            removeGeneratedFiles()
            resetVPNConfig(addon, 1)

    # Store the boot time and update the reboot reason
    addon.setSetting("boot_time", time.strftime('%Y-%m-%d %H:%M:%S'))
    addon.setSetting("last_boot_reason", addon.getSetting("boot_reason"))
    addon.setSetting("boot_reason", "unscheduled")
    # This is just formatted text to display on the settings page
    addon.setSetting("last_boot_text", "Last restart was at " + addon.getSetting("boot_time") + ", " + addon.getSetting("last_boot_reason"))
        
    # Need to go and request the main loop fetches the settings
    updateService("service initalisation")
    
    reconnect_vpn = False
    warned_monitor = False
    if addon.getSetting("monitor_paused") == "false":
        warned_monitor = True
        setVPNMonitorState("Started")
    else:
        setVPNMonitorState("Stopped")
    
    connect_on_boot_setting = addon.getSetting("vpn_connect_before_boot")
    connect_on_boot_ovpn = addon.getSetting("1_vpn_validated")
        
    # Timer values in seconds
    connection_retry_time_min = int(addon.getSetting("vpn_reconnect_freq"))
    connection_retry_time = connection_retry_time_min
    timer = 0
    cycle_timer = 0
    reboot_timer = 0
    seconds_to_reboot_check = 0
    reboot_time = ""
    reboot_day = ""
    last_file_check_time = 0
    
    last_cycle = ""
    delay_min = 2
    delay_max = 2
    delay = delay_max
    connection_errors = 0
    stop = False

    vpn_setup = True
    vpn_provider = ""
    playing = False
    
    accepting_changes = True
    
    infoTrace("service.py", "Starting VPN monitor service, platform is " + str(getPlatform()) + ", version is " + addon.getAddonInfo("version"))
    infoTrace("service.py", "Kodi build is " + xbmc.getInfoLabel('System.BuildVersion'))
    
    while not monitor.abortRequested():

        if stopRequested() or stop:
            if not stop:
				# Acknowledge that we've stopped so that the config can do things
				# Also shorten the delay so that we can be more responsive and kill any cycle attempt
                debugTrace("Service received a stop request")
                ackStop()                
                stop = True
                accepting_changes = False
                delay = delay_min
                clearVPNCycle()
            elif startRequested():
                debugTrace("Service received a start request")
				# When we're told we can start again, acknowledge that and reset the delay back up.
                ackStart()                
                stop = False
                accepting_changes = True
                delay = delay_max				
        else:	
			# See if there's been an update	requested from the main add-on
            if updateServiceRequested():
                # Need to get the addon again to ensure the updated settings are picked up
                addon = xbmcaddon.Addon()
                debugTrace("VPN monitor service was requested to run an update")
                accepting_changes = False
				# Acknowledge update needs to happen
                ackUpdate()

				# Refresh primary vpns
                debugTrace("Update primary VPNs from settings")
                refreshPrimaryVPNs()

                # Update the platform settings to make the right options appear
                refreshPlatformInfo()
                
                # See if the primary VPN Or boot setting has changed.  If it has, systemd needs fixing
                if (addon.getSetting("vpn_connect_at_boot") == "false" and connect_on_boot_setting == "true"):
                    addon.setSetting("vpn_connect_before_boot", "false")
                if (not connect_on_boot_setting == addon.getSetting("vpn_connect_before_boot")) or (not connect_on_boot_ovpn == addon.getSetting("1_vpn_validated")):
                    connect_on_boot_setting = addon.getSetting("vpn_connect_before_boot")
                    connect_on_boot_ovpn = addon.getSetting("1_vpn_validated")
                    infoTrace("service.py", "Updating systemd, connect before boot is " + connect_on_boot_setting + ", location is " + connect_on_boot_ovpn)
                    removeSystemd()
                    if connect_on_boot_setting == "true" and (not connect_on_boot_ovpn == ""):
                        copySystemdFiles()
                        addSystemd()
                
                # Determine if the VPN has been set up
                if primary_vpns[0] == "":
                    debugTrace("Found no VPNs, setup is invalid")
                    vpn_setup = False
                else:
                    debugTrace("Found " + str(len(primary_vpns)) + " VPNs, setup is valid")
                    vpn_setup = True
                    vpn_provider = addon.getSetting("vpn_provider_validated")
                    # If it's been set up, just check the VPN credentials file exists
                    # It can get deleted sometimes, like when reinstalling the addon
                    if usesPassAuth(getVPNLocation(vpn_provider)) and not xbmcvfs.exists(getCredentialsPath(addon)):
                        writeCredentials(addon)
                
                # Force a reboot timer check
                reboot_timer = 3600
                seconds_to_reboot_check = 0

				# Refresh filter lists
                debugTrace("Update filter lists from settings")
                refreshAddonFilterLists()

				# If the VPN is not deliberately disconnected, then connect it
                if vpn_setup and not getVPNState() == "off":
                    if getVPNState() == "started":
                        debugTrace("VPN is started on " + getVPNProfile() + " requesting " + getVPNRequestedProfile())
						# We're connected, but to the wrong VPN
                        if not getVPNRequestedProfile() == "":
                            if getVPNProfile() != getVPNRequestedProfile() :
                                reconnect_vpn = True
                    else:
                        debugTrace("VPN not started, state is " + getVPNState())
						# If we've just booted, then we won't have set the vpn_state property on the window
						# so it'll come back empty.  Use this to determine if we should connect on boot
                        if getVPNState() == "":
							# Just booted/started service.  If we're not connected at boot, then we're
							# deliberately disconnected until the user uses one of the connect options
                            if addon.getSetting("vpn_connect_at_boot") == "true":
                                if addon.getSetting("vpn_connect_before_boot") == "true" and isVPNTaskRunning():
                                    # Assume that the boot connect worked and populate the state variables
                                    debugTrace("Connecting to primary VPN during boot")
                                    setVPNProfile(addon.getSetting("1_vpn_validated"))
                                    setVPNProfileFriendly(addon.getSetting("1_vpn_validated_friendly"))
                                    setVPNState("started")
                                    setVPNRequestedProfile("")
                                    setVPNRequestedProfileFriendly("")
                                    setVPNLastConnectedProfile("")
                                    setVPNLastConnectedProfileFriendly("")
                                    setConnectionErrorCount(0)
                                    if addon.getSetting("display_location_on_connect") == "true":
                                        _, ip, country, isp = getIPInfo(addon)
                                        xbmcgui.Dialog().notification(addon_name, "Connected during boot to "+ getVPNProfileFriendly() + " via Service Provider " + isp + " in " + country + ". IP is " + ip + ".", getAddonPath(True, "/resources/connected.png"), 20000, False)
                                    else:
                                        xbmcgui.Dialog().notification(addon_name, "Connected during boot to "+ getVPNProfileFriendly(), getAddonPath(True, "/resources/connected.png"), 5000, False)
                                else:
                                    # No connect on boot (or it didn't work), so force a connect
                                    debugTrace("Connecting to primary VPN at Kodi start up")
                                    setVPNRequestedProfile(primary_vpns[0])
                                    setVPNRequestedProfileFriendly(primary_vpns_friendly[0])
                                    setVPNLastConnectedProfile("")
                                    setVPNLastConnectedProfileFriendly("")
                                    reconnect_vpn = True
                            else: 
                                # Not connecting at boot or not set up yet
                                setVPNState("off") 
                        elif getConnectionErrorCount() == 0:
							# Unknown state, and not in an error retry cycle, so try and reconnect immediately
                            debugTrace("Unknown VPN state so forcing reconnect")
                            reconnect_vpn = True
                accepting_changes = True						

            # This forces a connection validation after something stops playing
            if player.isPlaying():
                playing = True
            elif playing:
                playing = False
                timer = connection_retry_time + 1
                                        
			# This checks the connection is still good.  It will always do it whilst there's 
            # no playback but there's an option to suppress this during playback
            addon = xbmcaddon.Addon()
            if (not playing) or addon.getSetting("vpn_reconnect_while_playing") == "true":
                if vpn_setup and timer > connection_retry_time:
                    addon = xbmcaddon.Addon()
                    if addon.getSetting("vpn_reconnect") == "true":
                        if not isVPNConnected() and not (getVPNState() == "off"):
                            # Don't know why we're disconnected, but reconnect to the last known VPN
                            errorTrace("service.py", "VPN monitor service detected VPN connection " + getVPNProfile() + " is not running when it should be")
                            writeVPNLog()
                            if getVPNRequestedProfile() == "":
                                setVPNRequestedProfile(getVPNProfile())
                                setVPNRequestedProfileFriendly(getVPNProfileFriendly())
                            setVPNProfile("")
                            setVPNProfileFriendly("")
                            reconnect_vpn = True
                    connection_retry_time_min = int(addon.getSetting("vpn_reconnect_freq"))
                    timer = 0
                    

            # Check to see if it's time for a reboot (providing we need to, and nothing is playing)
            if (not playing) and reboot_timer >= seconds_to_reboot_check:
                reboot_timer = 0
                # Assume the next check is in an hour
                seconds_to_reboot_check = 3600
                # Check reboot check file if there is one
                reboot_file_name = addon.getSetting("reboot_file") 
                if xbmcvfs.exists(reboot_file_name):
                    stats = xbmcvfs.Stat(reboot_file_name)
                    file_check_time = stats.st_mtime()
                    if not file_check_time == last_file_check_time:
                        if last_file_check_time == 0:
                            # First check since reboot, just record the time
                            last_file_check_time = file_check_time
                        else:
                            if addon.getSetting("reboot_file_enabled") == "true":
                                if not xbmcgui.Dialog().yesno(addon_name, "System reboot about to happen because server rebooted.\nClick cancel within 30 seconds to abort.", "", "", "Reboot", "Cancel", 30000):
                                    infoTrace("service.py", "Server rebooted, going down for a reboot")
                                    addon.setSetting("boot_reason", "server rebooted")
                                    xbmc.executebuiltin("Reboot")
                                else:
                                    infoTrace("service.py", "Server rebooted, system reboot aborted by user")
                                    last_file_check_time = file_check_time
                # Refresh the reboot timer if it's changed in the seconds
                new_reboot_day = addon.getSetting("reboot_day")
                new_reboot_time = addon.getSetting("reboot_time")
                if not (new_reboot_day == reboot_day and new_reboot_time == reboot_time):
                    # Time has changed
                    reboot_day = new_reboot_day
                    reboot_time = new_reboot_time
                    setReboot("waiting")
                    if not reboot_day == "Off":
                        if xbmc.getInfoLabel("System.Date(DDD)") == reboot_day:
                            time_now_secs = getSeconds(time.strftime('%H:%M'))             
                            reboot_time_secs = getSeconds(reboot_time)
                            if time_now_secs > reboot_time_secs:
                                # Reboot is today but it's happened already already
                                setReboot("rebooted")
                    debugTrace("Reboot timer is " + reboot_day + " at " + reboot_time + ", " + getReboot())                
                if reboot_day == xbmc.getInfoLabel("System.Date(DDD)"):
                    if not getReboot() == "rebooted":
                        time_now_secs = getSeconds(time.strftime('%H:%M'))
                        reboot_time_secs = getSeconds(reboot_time)
                        if time_now_secs >= reboot_time_secs:
                            # Put up dialog warning of reboot and give user a chance to abort
                            if not xbmcgui.Dialog().yesno(addon_name, "Weekly system reboot about to happen.\nClick cancel within 30 seconds to abort.", "", "", "Reboot", "Cancel", 30000):
                                infoTrace("service.py", "Weekly reboot timer triggered (for " + reboot_day + " " + reboot_time + "), going down for a reboot.")
                                addon.setSetting("boot_reason", "weekly timer")
                                xbmc.executebuiltin("Reboot")
                            else:
                                infoTrace("service.py", "Weekly reboot timer aborted by user")
                            setReboot("rebooted")                           
                        else:
                            # Not time to reboot yet, so work out when to check again
                            seconds_to_reboot_check = reboot_time_secs - time_now_secs
                            # If it's more than an hour then restrict it to an hour to avoid the unreliability of
                            # the timer in the loop (which seems to drift/take longer depending on what's going on)
                            if seconds_to_reboot_check > 3600: seconds_to_reboot_check = 3600
                            debugTrace("Same day reboot, check again in " + str(seconds_to_reboot_check))
                else:
                    # Reboot on a different day, check status again in an hour.
                    setReboot("waiting")      
    
			# Fetch the path and name of the current addon
            current_path = xbmc.getInfoLabel("Container.FolderPath")
            current_name = xbmc.getInfoLabel("Container.FolderName")          
			# See if it's a different add-on the last time we checked.  If we don't know the
            # current_name (like when the player is playing within an addon), then skip making a change.
            if vpn_setup and not (xbmcgui.Window(10000).getProperty(last_addon) == current_name) and not current_name == "":
                if isVPNMonitorRunning():
                    # If the monitor is paused, we want to warn
                    warned_monitor = False
                    debugTrace("Encountered a new addon, " + current_path + " " + current_name)	
                    debugTrace("Previous addon was " + (xbmcgui.Window(10000).getProperty(last_addon)))
                    # Update window property to current addon
                    xbmcgui.Window(10000).setProperty(last_addon, current_name)
                    # Work out if we're using a primary VPN so if we have multiple filters
                    # and one of them is current we don't switch unncessarily
                    primary_found = 0
                    # # Adjust 10 below if changing number of conn_max
                    for i in range (0, 10):                    
                        if not primary_vpns[i] == "" and getVPNProfile() == primary_vpns[i]:
                            primary_found = i+1
                    # See if we should be filtering this addon
                    # -1 is no, 0 is disconnect, >0 is specific VPN
                    filter = isAddonFiltered(current_path, primary_found)                
                    if filter == 0:
                        infoTrace("service.py", "Disconnect filter found for addon " + current_name)
                        setVPNRequestedProfile("Disconnect")
                        setVPNRequestedProfileFriendly("Disconnect")
                        # Store the current profile for reconnection if we've not done previously
                        if getVPNLastConnectedProfile() == "" :
                            if getVPNState() == "started":
                                setVPNLastConnectedProfile(getVPNProfile())
                                setVPNLastConnectedProfileFriendly(getVPNProfileFriendly())
                            else:
                                setVPNLastConnectedProfile("Disconnect")
                                setVPNLastConnectedProfileFriendly("Disconnect")
                            debugTrace("Disconnecting, previous VPN stored as " + getVPNLastConnectedProfile())
                        reconnect_vpn = True
                    elif filter > 0:
                        infoTrace("service.py", "VPN filter " + primary_vpns[(filter-1)] + " found for addon " + current_name)
                        debugTrace("Switching from " + getVPNProfile() + " to " + primary_vpns[(filter-1)] + " primary found is " + str(primary_found))
                        # Connect to a specific VPN providing we're not connected already
                        if (not primary_vpns[(filter-1)] == getVPNProfile()) or not isVPNConnected():                        
                            setVPNRequestedProfile(primary_vpns[(filter-1)])
                            setVPNRequestedProfileFriendly(primary_vpns_friendly[(filter-1)])
                            # Store the current profile for reconnection if we've not done previously
                            if getVPNLastConnectedProfile() == "":
                                if getVPNState() == "started":
                                    setVPNLastConnectedProfile(getVPNProfile())
                                    setVPNLastConnectedProfileFriendly(getVPNProfileFriendly())
                                else:
                                    setVPNLastConnectedProfile("Disconnect")
                                    setVPNLastConnectedProfileFriendly("Disconnect")
                                debugTrace("Alternative VPN, previous VPN stored as " + getVPNLastConnectedProfile())
                            reconnect_vpn = True
                    else:
                        addon = xbmcaddon.Addon()
                        reconnect_filtering = addon.getSetting("vpn_reconnect_filtering")
                        debugTrace("No filter found, reconnect to previous is " + str(reconnect_filtering) + " reconnect state is " + getVPNState())
                        if reconnect_filtering == "true":
                            if not getVPNState() == "started":
                                # if we're not connected, reconnect to last known
                                if not getVPNLastConnectedProfile() == "":
                                    infoTrace("service.py", "Attempting reconnect to previous VPN " + getVPNLastConnectedProfile())
                                    debugTrace("Not connected, reconnecting to " + getVPNLastConnectedProfile())
                                    setVPNRequestedProfile(getVPNLastConnectedProfile())
                                    setVPNRequestedProfileFriendly(getVPNLastConnectedProfileFriendly())
                                    setVPNLastConnectedProfile("")
                                    setVPNLastConnectedProfileFriendly("")
                                    reconnect_vpn = True
                                # This bit of code is too aggressive as it causes a reconnect when the user has initiated a disconnect
                                #else:
                                #    setVPNRequestedProfile(primary_vpns[0])
                                #    setVPNRequestedProfileFriendly(primary_vpns_friendly[0])
                                #    reconnect_vpn = True
                            else:
                                # We're connected, but who knows to what.  If we've got a last connected set then reconnect 
                                # to that, otherwise just check we're still connected to what we think we are                            
                                if not getVPNLastConnectedProfile() == "":                                
                                    if not getVPNProfile() == getVPNLastConnectedProfile() or not isVPNConnected():
                                        debugTrace("Connected, but attempting reconnect to previous VPN" + getVPNLastConnectedProfile() + ", currently " + getVPNProfile())
                                        setVPNRequestedProfile(getVPNLastConnectedProfile())
                                        setVPNRequestedProfileFriendly(getVPNLastConnectedProfileFriendly())
                                        setVPNLastConnectedProfile("")
                                        setVPNLastConnectedProfileFriendly("")
                                        if getVPNRequestedProfile() == "Disconnect":
                                            infoTrace("service.py", "VPN was previously disconnected, disconnecting")
                                        else:
                                            infoTrace("service.py", "Reconnecting to previous VPN, " + getVPNRequestedProfile())
                                        reconnect_vpn = True
                                else:
                                    # If there's no history, just check we're still connected
                                    if not isVPNConnected():
                                        debugTrace("Connection bad, reconnecting to " + getVPNProfile())
                                        infoTrace("service.py", "VPN connection bad, reconnecting to last profile or primary")
                                        writeVPNLog()
                                        setVPNLastConnectedProfile("")
                                        setVPNLastConnectedProfileFriendly("")
                                        reconnect_vpn = True
                                        if getVPNProfile() == "":
                                            # Reconnect to primary if we can't tell what we should be connected to
                                            setVPNRequestedProfile(primary_vpns[0])
                                            setVPNRequestedProfileFriendly(primary_vpns_friendly[0])
                                        else:
                                            # Reconnect to current profile
                                            setVPNRequestedProfile(getVPNProfile())
                                            setVPNRequestedProfileFriendly(getVPNProfileFriendly())                                                                                
                                            setVPNProfile("")
                                            setVPNProfileFriendly("")                                     
                else:
                    # Monitor is paused, warn user if not done so previously
                    if not warned_monitor:
                        warned_monitor = True
                        xbmcgui.Dialog().notification(addon_name, "Add-on filtering paused", getAddonPath(True, "/resources/warning.png"), 10000, False)
                    
            # See if the addon is requesting to cycle through the VPNs
            cycle_requested = getVPNCycle()
            if vpn_setup and not cycle_requested == "":

                # Wait a short period, and then just grab the lock anyway.
                forceCycleLock()
                debugTrace("Got forced cycle lock in cycle part of service")
                
                # Reset the timer if this is a different request than last time we looked
                if not cycle_requested == last_cycle:
                    debugTrace("New Cycling VPN connection " + cycle_requested)
                    last_cycle = cycle_requested
                    cycle_timer = 0
                
                # Increment cycle counter so that user has the chance to cycle multiple times before connection
                cycle_timer = cycle_timer + delay

                # Let's connect!
                if cycle_timer > 9:
                    debugTrace("Running VPN cycle request " + cycle_requested + ", current VPN is " + getVPNProfile())
                    if not (cycle_requested == "Disconnect" and getVPNProfile() == "") and (not cycle_requested == getVPNProfile()):
                        infoTrace("service.py", "Cycle requested connection to " + cycle_requested)
                        setVPNRequestedProfile(cycle_requested)
                        if cycle_requested == "Disconnect":
                            setVPNRequestedProfileFriendly("Disconnect")
                        else:
                            setVPNRequestedProfileFriendly(getFriendlyProfileName(cycle_requested))
                        setVPNLastConnectedProfile("")
                        setVPNLastConnectedProfileFriendly("")
                        reconnect_vpn = True
                    else:
                        # Display the full details for those with this option switched on otherwise just let the notification box disappear
                        if addon.getSetting("display_location_on_connect") == "true":
                            _, ip, country, isp = getIPInfo(addon)
                            xbmcgui.Dialog().notification(addon_name, "Connected to "+ getVPNProfileFriendly() + " via Service Provider " + isp + " in " + country + ". IP is " + ip + ".", getAddonPath(True, "/resources/connected.png"), 20000, False)
                    clearVPNCycle()
                    cycle_timer = 0
                
                freeCycleLock()

            # Connect or disconnect in response to an API call
            api_command = getAPICommand()
            if vpn_setup and not api_command == "":
                infoTrace("service.py", "API command found, " + api_command)
                setVPNRequestedProfile(api_command)
                if api_command == "Disconnect":
                    setVPNRequestedProfileFriendly("Disconnect")
                else:
                    setVPNRequestedProfileFriendly(getFriendlyProfileName(api_command))
                clearAPICommand()
                reconnect_vpn = True
                
			# Somewhere above we've requested we mess with the connection...
            if vpn_setup and reconnect_vpn:
                addon = xbmcaddon.Addon()
                debugTrace("Running VPN (dis)connect request " + getVPNRequestedProfile() + ", current is " + getVPNProfile())
                
                # Wait a short period, and then just grab the lock anyway.
                forceCycleLock()
                debugTrace("Got forced cycle lock in connection part of service")
                
				# Stop the VPN and reset the connection timer
                # Surpress a reconnection to the same unless it's become disconnected
                if (not getVPNRequestedProfile() == getVPNProfile()) or (getVPNRequestedProfile() == getVPNProfile() and not isVPNConnected()):                    

                    # Stop any media playing before switching VPNs around   
                    if player.isPlaying(): player.stop()
                    
                    # Stop any existing VPN
                    debugTrace("Stopping VPN before any new connection attempt")
                    if getVPNState() == "started":
                        stopVPNConnection()
                        if getVPNRequestedProfile() == "Disconnect" and addon.getSetting("display_location_on_connect") == "true":
                            _, ip, country, isp = getIPInfo(addon)
                            xbmcgui.Dialog().notification(addon_name, "Disconnected from VPN. Service Provider is " + isp + " in " + country + ". IP is " + ip + ".", getAddonPath(True, "/resources/disconnected.png"), 20000, False)
                        else:
                            xbmcgui.Dialog().notification(addon_name, "Disconnected", getAddonPath(True, "/resources/disconnected.png"), 3000, False)
                        infoTrace("service.py", "Disconnect from VPN")
                    else:
                        # Just incase we're in a weird unknown state, this should clear things up
                        stopVPNConnection()
                        debugTrace("Unconnected state, " + getVPNState() + " so disconnected anyway")
                    
                    timer = 0
                
                    # Don't reconnect if this is a disconnect request, or there is nothing to connect to (primary not set)
                    if not getVPNRequestedProfile() == "Disconnect":
                        if not getVPNRequestedProfile() == "":
                            infoTrace("service.py", "Connecting to VPN profile " + getVPNRequestedProfile())
                            xbmcgui.Dialog().notification(addon_name, "Connecting to "+ getVPNRequestedProfileFriendly(), getAddonPath(True, "/resources/locked.png"), 5000, False)
                            state = startVPNConnection(getVPNRequestedProfile())
                            if not state == connection_status.CONNECTED:
                                if state == connection_status.AUTH_FAILED:
                                    # If authentication fails we don't want to try and reconnect
                                    # Everything will get reset below if timer is 0 but we'll make
                                    # like the VPN state is off deliberately to avoid reconnect
                                    xbmcgui.Dialog().notification(addon_name, "Error authenticating with VPN, retry or update credentials.", xbmcgui.NOTIFICATION_ERROR, 10000, True)
                                    setVPNState("off")
                                else:
                                    connection_errors = getConnectionErrorCount() + 1
                                    if connection_errors > 9:
                                        if addon.getSetting("vpn_reconnect_reboot") == "true" and connection_errors == 10:
                                            if not xbmcgui.Dialog().yesno(addon_name, "Cannot connect to VPN, rebooting system.\nClick cancel within 30 seconds to abort.", "", "", "Reboot", "Cancel", 30000):
                                                infoTrace("service.py", "Reboot because of VPN connection errors.")
                                                addon.setSetting("boot_reason", "VPN errors")
                                                xbmc.executebuiltin("Reboot")
                                            else:
                                                infoTrace("service.py", "VPN connection reboot aborted by user")
                                        # Too many errors, limit retry to once every hour
                                        connection_retry_time = 3600
                                    else:
                                        # Try to reconnect increasing frequency (a minute longer each time)
                                        connection_retry_time = 60 * connection_errors
                                    setConnectionErrorCount(connection_errors)
                                    xbmcgui.Dialog().notification(addon_name, "Error connecting to VPN, check network. Retrying in " + str((connection_retry_time/60)) + " minutes.", xbmcgui.NOTIFICATION_ERROR, 10000, True)
                                    timer = 1
                                # Want to kill any running process if it's not completed successfully
                                stopVPNConnection()
                                errorTrace("service.py", "VPN connect to " + getVPNLastConnectedProfile() + " has failed, VPN error was " + str(state))
                                writeVPNLog()
                                debugTrace("VPN connection failed, errors count is " + str(connection_errors) + " connection timer is " + str(connection_retry_time))
                            else:
                                if ifDebug(): writeVPNLog()
                                if addon.getSetting("display_location_on_connect") == "true":
                                    _, ip, country, isp = getIPInfo(addon)
                                    xbmcgui.Dialog().notification(addon_name, "Connected to "+ getVPNProfileFriendly() + " via Service Provider " + isp + " in " + country + ". IP is " + ip + ".", getAddonPath(True, "/resources/connected.png"), 20000, False)
                                else:
                                    xbmcgui.Dialog().notification(addon_name, "Connected to "+ getVPNProfileFriendly(), getAddonPath(True, "/resources/connected.png"), 5000, False)
                        else:
                            xbmcgui.Dialog().notification(addon_name, "Filtering " + current_name + " but no validated connection available.", getAddonPath(True, "/resources/warning.png"), 10000, False)
                    else:                                               
                        setConnectionErrorCount(0)
                        setVPNState("off")
                
                # Reset a bunch of things if we've connected/disconnected successfully
                if timer == 0:                    
                    setConnectionErrorCount(0)
                    setVPNRequestedProfile("")
                    setVPNRequestedProfileFriendly("")
                    clearVPNCycle()
                    connection_retry_time = connection_retry_time_min
				
                # Let the cycle code run again
                freeCycleLock()
                
                reconnect_vpn = False          

			                    
        # Sleep/wait for abort
        if monitor.waitForAbort(delay):
            # Abort was requested while waiting. We should exit
            infoTrace("service.py", "Abort received, shutting down service")
            break
            
        timer = timer + delay
        reboot_timer = reboot_timer + delay
        