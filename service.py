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
#    Service module for addon

import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import os
import time
import random
import datetime
import urllib2
import re
import string
from libs.common import updateServiceRequested, ackUpdate, setVPNProfile, getVPNProfileFriendly, setVPNProfileFriendly, getReconnectTime
from libs.common import getVPNRequestedProfile, setVPNRequestedProfile, getVPNRequestedProfileFriendly, setVPNRequestedProfileFriendly, getIPInfo
from libs.common import setVPNState, getVPNState, stopRequested, ackStop, startRequested, ackStart, updateService, stopVPNConnection, startVPNConnection
from libs.common import getVPNLastConnectedProfile, setVPNLastConnectedProfile, getVPNLastConnectedProfileFriendly, setVPNLastConnectedProfileFriendly
from libs.common import getVPNCycle, clearVPNCycle, writeCredentials, getCredentialsPath, getFriendlyProfileName, isVPNMonitorRunning, setVPNMonitorState
from libs.common import getConnectionErrorCount, setConnectionErrorCount, getAddonPath, isVPNConnected, resetVPNConfig, forceCycleLock, freeCycleLock
from libs.common import getAPICommand, clearAPICommand, fixKeymaps, setConnectTime, getConnectTime, requestVPNCycle, failoverConnection
from libs.common import forceReconnect, isForceReconnect, updateIPInfo, updateAPITimer, wizard, connectionValidated, getVPNRequestedServer
from libs.common import getVPNServer, setReconnectTime, configUpdate, resumeStartStop, suspendStartStop, checkDirectory, clearServiceState, getVPNServerFromFile
from libs.vpnplatform import getPlatform, platforms, connection_status, getAddonPath, writeVPNLog, supportSystemd, addSystemd, removeSystemd, copySystemdFiles
from libs.vpnplatform import isVPNTaskRunning, updateSystemTime, fakeConnection, fakeItTillYouMakeIt, generateVPNs, writeVPNConfiguration
from libs.utility import debugTrace, errorTrace, infoTrace, ifDebug, newPrint, setID, setName, setShort, setVery, running, setRunning, now, isCustom
from libs.vpnproviders import removeGeneratedFiles, cleanPassFiles, fixOVPNFiles, getVPNLocation, usesPassAuth, clearKeysAndCerts, checkForVPNUpdates
from libs.vpnproviders import populateSupportingFromGit, isAlternative, regenerateAlternative, getAlternativeLocation, updateVPNFile, checkUserDefined
from libs.vpnproviders import getUserDataPath, getAlternativeMessages, postConnectAlternative
from libs.access import getVPNURL, setVPNURL, getVPNProfile
from libs.vpnapi import VPNAPI

# Set the addon name for use in the dialogs
# It's in a finite loop because it seems to take a while for Kodi to settle
count = 0
while count < 6:
    try:
        e = None
        addon = xbmcaddon.Addon()
        addon_name = addon.getAddonInfo('name')
        setName(addon_name)
        addon_id = addon.getAddonInfo('id')
        setID(addon_id)
        addon_short = addon.getSetting("vpn_short")
        setShort(addon_short)
        addon_very = addon.getSetting("vpn_very")
        setVery(addon_very)
        xbmc.sleep(100)
        break
    except Exception as e:
        # Try again in 5 seconds
        count += 1
        xbmc.sleep(5000)

if not e == None:
    errorTrace("service.py", "Couldn't start service after " + str(count) + " attempts")
    errorTrace("service.py", str(e))
    raise e

debugTrace("-- Entered service.py --")

# Window property constants
last_addon = 'VPN_Manager_Last_Addon'

# Lists of primary VPNs and their friendly names (so we don't have to keep pattern matching it)
primary_vpns = []
primary_vpns_friendly = []

accepting_changes = False

streaming = False

abort = False

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
    addon.setSetting("platform", str(getPlatform()))
    
    # Determine if systemd is available so that extra options appear in the settings menu
    if supportSystemd():
        new_sysd = "true"
    else:
        new_sysd = "false"
    addon.setSetting("show_preboot_connect", new_sysd)
    
    # Some tracing that we might want to do
    if xbmcvfs.exists(getUserDataPath("JSONTRACE.txt")):
        addon.setSetting("vpn_enable_json", "true")
    else:
        addon.setSetting("vpn_enable_json", "false")

def checkConnections():
    # Check that all of the connections exist
    # Adjust 11 below if changing number of conn_max
    for i in range (1, 11):        
        next_conn = (addon.getSetting(str(i)+"_vpn_validated"))
        if not next_conn == "" and not xbmcvfs.exists(next_conn):
            errorTrace("service.py", "Checking connections and couldn't find connection " + str(i) + ", " + next_conn)
            return False
    return True


# Given hh:mm, return the number of seconds into a day this represents
def getSeconds(hour_min):
    return int(hour_min[0:2])*3600 + int(hour_min[3:5])*60


# Quit event is being intercepted so this replaces the monitor.waitForAbort
# Time is measured in 1000s of a second, not whole seconds
def waitForAbort( time ):
    if not abort: xbmc.sleep(time)
    return abort

    
def abortRequested():
    return abort

    
# Monitor class which will get called when the settings change    
class KodiMonitor(xbmc.Monitor):

    # This gets called every time a setting is changed either programmatically or via the settings dialog.
    # We do our best to ignore settings changing as part of common processes so that we don't do too much
    # work refreshing things, but there are a few calls that will happen anyway (and better to do this)
    # than to miss out on an update that a user makes via the GUI.
    def onSettingsChanged( self ):
        if accepting_changes and configUpdate():
            debugTrace("Requested update to service process via settings monitor")
            updateService("KodiMonitor")
    
    # Intercept all notifications and deal with a couple of them
    def onNotification( self, sender, method, data):
        global abort
        if method == "System.OnWake":
            addon = xbmcaddon.Addon()
            if addon.getSetting("vpn_force_reconnect_after_wake") == "true":
                debugTrace("Forcing a reconnect on wake")
                forceReconnect("True")
        if method == "System.OnQuit":
            debugTrace("Received a quit notification")
            abort = True
            

# Player class which will get called when a video starts/stops            
class KodiPlayer(xbmc.Player):
    
    def __init__ (self):
        xbmc.Player.__init__(self)
        self.logger = None

    def onPlayBackStarted(self, *arg):
        global streaming
        try:
            filename = self.getPlayingFile()
            addon = xbmcaddon.Addon()
            all_ids = addon.getSetting("vpn_stream_ids").split()
            stream_ids = []
            exclude_ids = []
            for id in all_ids:
                if id.startswith("!"):
                    exclude_ids.append(id[1:])
                else:
                    stream_ids.append(id)
            streaming = False
            for stream_id in stream_ids:
                if filename.startswith(stream_id):
                    streaming = True
                    for exclude_id in exclude_ids:
                        if filename.startswith(exclude_id):
                            streaming = False
                    break
            if streaming: debugTrace("Starting streaming media " + filename)
        except Exception as e:
            # This is a pass because in some circumstances, the file name can be unavailable and we'll end up here
            pass
        
# Probably don't need to do this, but I'm hoping it introduces an element of randomness during install
# so that the running() check isn't perfectly synced with another task running at the same time
if xbmcvfs.exists(getAddonPath(True, "INSTALL.txt")): stopVPNConnection() 

if __name__ == '__main__' and not running():   

    # This and the running() check above is to work around a Kodi 17 bug that starts a service twice after install
    setRunning(True)
    
    shutdown = False
    stop_vpn = False

    infoTrace("service.py", "Starting VPN monitor service, platform is " + str(getPlatform()) + ", version is " + addon.getAddonInfo("version"))
    infoTrace("service.py", "Kodi build is " + xbmc.getInfoLabel('System.BuildVersion'))
    infoTrace("service.py", "Addon path is " + getAddonPath(True, ""))
    
    # Initialise the monitor classes
    monitor = KodiMonitor()
    player = KodiPlayer() 
    
    # Initialise some variables we'll be using repeatedly
    addon = xbmcaddon.Addon()
    filters = VPNAPI()
    
    if not xbmcvfs.exists(getAddonPath(True, "connect.py")):
        xbmcgui.Dialog().ok(addon_name, "You've installed " + addon_short + " incorrectly and the add-on won't work.  Check the log, install a Github released build or install from the repository.")
        errorTrace("service.py", "Install is in the wrong place, expecting to find the add-on installed in " + getAddonPath(True,""))
    
    # See if this is a new install...we might want to do things here
    if xbmcvfs.exists(getAddonPath(True, "INSTALL.txt")):
        xbmcvfs.delete(getAddonPath(True, "INSTALL.txt"))
        # Stopping the connection so if this is an upgrade we don't assume things about connect on boot
        stopVPNConnection()
        # This is just wiping out the old way of using pre-generated ovpn files before
        # moving to the brave new world of generating them when they're needed
        stored_version = addon.getSetting("version_number").strip()
        if stored_version == "":
            infoTrace("service.py", "New install, resetting the world " + addon.getSetting("version_number"))
            removeGeneratedFiles()
            resetVPNConfig(addon, 1)
        else:
            # Do a bunch of version number dependent tests
            last_version = int(stored_version.replace(".", ""))
            # This fixes a problem with the 2.2 version that causes the profiles to be regenerated
            if last_version == 22: last_version = 220
            # Forces the IP provider to be the default/best rather than a selected on
            if last_version < 250:
                addon.setSetting("ip_info_source", "Auto select")
            if last_version < 400:
                removeGeneratedFiles()
                resetVPNConfig(addon, 1)
                xbmcgui.Dialog().ok(addon_name, "Thanks for using " + addon_short + "! V4.0 downloads and updates VPN files separately, making updates quicker.  Please re-validate your connections to download the files for your VPN provider.")
            reset_everything = False
            if addon.getSetting("vpn_provider_validated") == "PureVPN" or addon.getSetting("vpn_provider") == "PureVPN":
                xbmcgui.Dialog().ok(addon_name, "Support for PureVPN has been removed as they now support their own add-on.  See https://www.purevpn.com/blog/kodi-vpn/")
                reset_everything = True
            if not isCustom() and last_version < 500:
                if addon.getSetting("vpn_provider_validated") == "UserDefined" and checkUserDefined("NordVPN"):
                    xbmcgui.Dialog().ok(addon_name, "Support for NordVPN has been re-introduced to use the NordVPN API to dynamically manage connections.  Please consider using built in support.")
                if addon.getSetting("vpn_provider_validated") == "NordVPN":
                    xbmcgui.Dialog().ok(addon_name, "Support for NordVPN has been improved to use the NordVPN API to dynamically manage connections.  Please re-validate your connections to continue to use NordVPN.")
                    reset_everything = True
            if reset_everything:
                removeGeneratedFiles()
                resetVPNConfig(addon, 1)
                addon.setSetting("vpn_username", "")
                addon.setSetting("vpn_username_validated", "")
                addon.setSetting("vpn_password", "")
                addon.setSetting("vpn_password_validated", "")
                addon.setSetting("vpn_locations_list", "")
                addon.setSetting("vpn_provider", "")
                addon.setSetting("vpn_provider_validated", "")
                addon.setSetting("vpn_wizard_enabled", "true")
                removeSystemd()
            if last_version < 420:
                fixKeymaps()
            if last_version < 430:
                if not addon.getSetting("reboot_day") == "Off" or addon.getSetting("reboot_file_enabled") == "true":
                    xbmcgui.Dialog().ok(addon_name, "Thanks for installing v4.3.0!  The system reboot function has been improved and moved to the Zomboided Tools add-on, also in the Zomboided repository.  This add-on will no longer reboot your system.")
            if last_version < 497:
                if addon.getSetting("vpn_wizard_run") == "false": addon.setSetting("vpn_wizard_enabled", "true")
                if addon.getSetting("vpn_wizard_run") == "true": addon.setSetting("vpn_wizard_enabled", "false")
            if last_version < 602:
                if not addon.getSetting("vpn_provider_validated") == "":
                    addon.setSetting("vpn_validated", "true")
            if last_version < 610:
                if getPlatform() == platforms.WINDOWS or addon.getSetting("openvpn_no_path") == "true":
                    addon.setSetting("openvpn_no_path", "true")
                    addon.setSetting("openvpn_path", "")
                    
        addon.setSetting("version_number", addon.getAddonInfo("version"))
   
    # If the addon was running happily previously (like before an uninstall/reinstall or update)
    # then regenerate the OVPNs for the validated provider.
    primary_path = addon.getSetting("1_vpn_validated")

    # During an upgrade, some states stored on the window will be wrong so reset them as if it were a restart
    setVPNState("")
    clearServiceState()

    if not primary_path == "" and not xbmcvfs.exists(primary_path):
        vpn_provider = getVPNLocation(addon.getSetting("vpn_provider_validated"))
        infoTrace("service.py", "New install, but was using good VPN previously (" + vpn_provider + ", " + primary_path + ").  Regenerate OVPNs")
        
        if not isAlternative(vpn_provider):
            populateSupportingFromGit(vpn_provider)
            if not checkDirectory(vpn_provider) or not fixOVPNFiles(vpn_provider, addon.getSetting("vpn_locations_list")) or not checkConnections():
                errorTrace("service.py", "VPN connection is not available for " + vpn_provider + " with list " + addon.getSetting("vpn_locations_list") + ", need to revalidate")
                xbmcgui.Dialog().ok(addon_name, "One of the VPN connections you were using previously is no longer available.  Please re-validate all connections.")
                removeGeneratedFiles()
                resetVPNConfig(addon, 1)
        else:
            if not checkDirectory(vpn_provider) or not regenerateAlternative(vpn_provider):
                # Clear the provider if it couldn't be regenerated
                errorTrace("service.py", "VPN connection is not available for " + vpn_provider + " with list " + addon.getSetting("vpn_locations_list") + ", need to revalidate")
                removeGeneratedFiles()
                resetVPNConfig(addon, 1)
        
            
    # Make sure the right options appear in the settings menu
    refreshPlatformInfo()        
            
    # This will adjust the system time on Linux platforms if it's too far adrift from reality
    if getPlatform() == platforms.LINUX and addon.getSetting("fix_system_time") == "true":
        curr_time = now()
        last_conn_time = getConnectTime(addon)
        if last_conn_time > curr_time:
            infoTrace("service.py", "System time was in the past, updating it to " + datetime.datetime.fromtimestamp(last_conn_time).strftime('%Y-%m-%d %H:%M:%S'))
            updateSystemTime(last_conn_time)
            
    # Store the boot time and update the reboot reason
    addon.setSetting("boot_time", time.strftime('%Y-%m-%d %H:%M:%S'))
    addon.setSetting("last_boot_reason", addon.getSetting("boot_reason"))
    addon.setSetting("boot_reason", "unscheduled")
    # This is just formatted text to display on the settings page
    addon.setSetting("last_boot_text", "Last restart was at " + addon.getSetting("boot_time") + ", " + addon.getSetting("last_boot_reason"))

    # Check the keymaps for this add-on are intact
    if fixKeymaps():
        xbmcgui.Dialog().ok(addon_name, "The keymap for this add-on had been renamed.  It's been fixed now but you must restart for the keymap to take effect.") 
        
    # Determine whether generation of VPN files is enabled
    if generateVPNs():
        addon.setSetting("allow_vpn_generation", "true")
    else:
        addon.setSetting("allow_vpn_generation", "false")
    
    addon = xbmcaddon.Addon()
    
    # Need to go and request the main loop fetches the settings
    updateService("service initalisation")
    
    reconnect_vpn = False
    warned_monitor = False
    if addon.getSetting("monitor_paused") == "true":
        setVPNMonitorState("Stopped")
    else:
        warned_monitor = True
        setVPNMonitorState("Started")
        
    connect_on_boot_setting = addon.getSetting("vpn_connect_before_boot")
    connect_on_boot_ovpn = addon.getSetting("1_vpn_validated")

    # Clear the URL variable so that it'll get reset if/when needed
    setVPNURL("")

    # Delay start up if required
    connect_delay = addon.getSetting("vpn_connect_delay")
    if connect_delay.isdigit(): connect_delay = int(connect_delay)
    else: connect_delay = 0
    if connect_delay > 0 and not connect_on_boot_setting == "true":
        infoTrace("service.py", "Delaying all VPN connections for " + str(connect_delay) + " seconds")
        xbmcgui.Dialog().notification(addon_name, "Delaying start for " + str(connect_delay) + " seconds.", getAddonPath(True, "/resources/paused.png"), 5000, False)
        xbmc.sleep(connect_delay*1000)
    
    # Timer values in seconds
    connection_retry_time_min = int(addon.getSetting("vpn_reconnect_freq"))
    connection_retry_time = connection_retry_time_min
    timer = 0
    cycle_timer = 0
    last_file_check_time = 0
    
    last_cycle = ""
    delay_min = 2
    delay_max = 4
    delay = delay_max
    connection_errors = 0
    stop = False
    
    last_window_id = 0

    vpn_setup = True
    vpn_provider = ""
    playing = False
    
    accepting_changes = True
    
    # If no connection has been set up, offer to run the wizard
    if (not connectionValidated(addon)) and addon.getSetting("vpn_wizard_enabled") == "true":
        state = suspendStartStop()
        wizard()
        resumeStartStop(state)
    
    addon = xbmcaddon.Addon()
    while not abortRequested():
    
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
            # See if there's been an update requested from the main add-on
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
                if getPlatform() == platforms.LINUX and ((not connect_on_boot_setting == addon.getSetting("vpn_connect_before_boot")) or (not connect_on_boot_ovpn == addon.getSetting("1_vpn_validated"))):
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
                    vpn_count = 0
                    for next_vpn in primary_vpns:
                        if next_vpn == "": break
                        vpn_count += 1
                    debugTrace("Found " + str(vpn_count) + " VPNs, setup is valid")
                    vpn_setup = True
                    vpn_provider = addon.getSetting("vpn_provider_validated")
                    # If it's been set up, just check the VPN credentials file exists
                    # It can get deleted sometimes, like when reinstalling the addon
                    if usesPassAuth(getVPNLocation(vpn_provider)) and not xbmcvfs.exists(getCredentialsPath(addon)):
                        writeCredentials(addon)

                # Flag that filter and VPN lists have changed
                debugTrace("Flag lists have changed")
                xbmcgui.Window(10000).setProperty("VPN_Manager_Lists_Last_Refreshed", str(now()))
                
                # (Re)set the reconnect time of the existing connection
                if getVPNState() == "started":
                    r = int(addon.getSetting("auto_reconnect_vpn"))
                    if r == 0 and getReconnectTime() > 0: setReconnectTime(addon, now())
                    elif r > 0 and getReconnectTime() == 0: setReconnectTime(addon, now())
                
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
                                    setVPNURL(getVPNServerFromFile(getVPNProfile()))
                                    setConnectionErrorCount(0)
                                    notification_time = 5000
                                    if fakeConnection():
                                        icon = "/resources/faked.png"
                                    else:
                                        icon = "/resources/connected.png"
                                    if not checkForVPNUpdates(getVPNLocation(addon.getSetting("vpn_provider_validated")), True):
                                        notification_title = addon_name
                                    else:
                                        notification_title = addon_short + ", update available"
                                        icon = "/resources/update.png"
                                        notification_time = 8000
                                    addon = xbmcaddon.Addon()
                                    if addon.getSetting("display_location_on_connect") == "true":
                                        _, ip, country, isp = getIPInfo(addon)
                                        xbmcgui.Dialog().notification(notification_title, "Connected during boot to "+ getVPNProfileFriendly() + " via Service Provider " + isp + " in " + country + ". IP is " + ip + ".", getAddonPath(True, icon), 20000, False)
                                    else:
                                        xbmcgui.Dialog().notification(notification_title, "Connected during boot to "+ getVPNProfileFriendly(), getAddonPath(True, icon), notification_time, False)
                                    # Record when the connection happened
                                    setConnectTime(addon)
                                else:
                                    # No connect on boot (or it didn't work), so force a connect
                                    debugTrace("Failed to connect to primary VPN at Kodi start up")
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
                # Sleep before accepting changes just in case there are callbacks to the settings monitor outstanding
                xbmc.sleep(1000)
                accepting_changes = True                        

            # This forces a connection validation after something stops playing
            if player.isPlaying():
                playing = True
            elif playing:
                playing = False
                timer = connection_retry_time + 1
                                        
            # This checks the connection is still good.  It will always do it whilst there's 
            # no playback but there's an option to suppress this during playback
            try:
                addon = xbmcaddon.Addon()
            except:
                errorTrace("service.vpn", "Failed to get addon ID hopefully because of an upgrade.  Quitting service")
                break
            if (not playing) or (addon.getSetting("vpn_reconnect_while_playing") == "true" or (addon.getSetting("vpn_reconnect_while_streaming") == "true" and streaming)):
                if vpn_setup and (timer > connection_retry_time or (not playing and getConnectionErrorCount() == 0)):
                    if addon.getSetting("vpn_reconnect") == "true":
                        if not (getVPNState() == "off") and not isVPNConnected():
                            # Don't know why we're disconnected, but reconnect to the last known VPN
                            errorTrace("service.py", "VPN monitor service detected VPN connection " + getVPNProfile() + " is not running when it should be")
                            writeVPNConfiguration(getVPNProfile())
                            writeVPNLog()
                            if getVPNRequestedProfile() == "":
                                setVPNRequestedProfile(getVPNProfile())
                                setVPNRequestedProfileFriendly(getVPNProfileFriendly())
                            setVPNProfile("")
                            setVPNProfileFriendly("")
                            reconnect_vpn = True
                    connection_retry_time_min = int(addon.getSetting("vpn_reconnect_freq"))
                    timer = 0
            
            # Check to see if a reconnect is needed
            if (not playing) and vpn_setup: 
                rt = getReconnectTime()                
                if rt > 0:
                    if getVPNState() == "started" and isVPNConnected() and rt < now():
                        debugTrace("Reconnecting as connection has been alive for " + addon.getSetting("auto_reconnect_vpn") + " hours")
                        forceReconnect("True")
            
            # This will force a reconnect to happen, unless the VPN state is off
            if isForceReconnect() and not (getVPNState() == "off"):
                forceReconnect("")
                infoTrace("service.py", "Forcing a reconnection")
                writeVPNConfiguration(getVPNProfile())
                writeVPNLog()
                setVPNRequestedProfile(getVPNProfile())
                setVPNRequestedProfileFriendly(getVPNProfileFriendly())
                setVPNProfile("")
                setVPNProfileFriendly("")
                reconnect_vpn = True
    
            # Fetch the path and name of the current addon and the current active window
            current_path = xbmc.getInfoLabel("Container.FolderPath")
            current_name = xbmc.getInfoLabel("Container.FolderName")
            current_window_id = xbmcgui.getCurrentWindowId()
            
            try_to_filter = False
            
            # See if the window ID has changed since last time
            if not current_window_id == last_window_id:
                if addon.getSetting("display_window_id") == "true":
                    xbmcgui.Dialog().notification(addon_name, "Window ID is now " + str(current_window_id), getAddonPath(True, "/resources/display.png"), 5000, False)
                    infoTrace("service.py", "Window ID is now " + str(current_window_id))
                debugTrace("Encountered a new window ID " + str(current_window_id)) 
                debugTrace("Previous window ID was " + str(last_window_id)) 
                last_window_id = current_window_id
                try_to_filter = True

            # See if the addon name has changed since last time.  Check for current_name being blank for
            # when an addon uses a window with no name (like when it's playing back video)
            if (not xbmcgui.Window(10000).getProperty(last_addon) == current_name) and (not current_name == ""):
                debugTrace("Encountered a new addon " + current_path + " " + current_name)  
                debugTrace("Previous addon was " + (xbmcgui.Window(10000).getProperty(last_addon)))    
                xbmcgui.Window(10000).setProperty(last_addon, current_name)
                try_to_filter = True
                
            # Filter on the window ID and name to see if the VPN connection should change
            if vpn_setup and try_to_filter:
                if isVPNMonitorRunning():
                    # If the monitor is paused, we want to warn
                    warned_monitor = False            
                    # See if we should be filtering this addon
                    # -1 is no, 0 is disconnect, >0 is specific VPN
                    filter = filters.isFiltered(current_path, current_window_id)                
                    if filter == 0:
                        # Don't need a VPN, so disconnect if a VPN is running
                        if getVPNState() == "started":
                            infoTrace("service.py", "Disconnect filter found for window " + str(current_window_id) + " or addon " + current_name)
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
                        # Connect to a specific VPN providing we're not connected already
                        if (not primary_vpns[(filter-1)] == getVPNProfile()) or not isVPNConnected():                        
                            infoTrace("service.py", "VPN filter " + primary_vpns[(filter-1)] + " found for window " + str(current_window_id) + " or addon " + current_name)
                            if not primary_vpns[(filter-1)] == "":                                
                                debugTrace("Switching from " + getVPNProfile() + " to " + primary_vpns[(filter-1)])
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
                                xbmcgui.Dialog().notification(addon_name, "Filtering " + current_name + " but no validated connection available.", getAddonPath(True, "/resources/warning.png"), 10000, False)
                    else:
                        # No filter found, so ensure we're using the right VPN (ie the last connected).  The only reason not to do this
                        # is if the current_name is blank, at which point we can't make sensible decisions about what to do.  This can
                        # be the case when the window ID has change (and has been ignored by the filters), and Kodi is using a non-addon
                        # like the full screen player or one of it's own windows
                        if not current_name == "":
                            addon = xbmcaddon.Addon()
                            reconnect_filtering = addon.getSetting("vpn_reconnect_filtering")
                            debugTrace("No filter found, reconnect to previous is " + str(reconnect_filtering) + " reconnect state is " + getVPNState())
                            if reconnect_filtering == "true":
                                if not getVPNState() == "started":
                                    # if we're not connected, reconnect to last known
                                    if not getVPNLastConnectedProfile() == "":
                                        infoTrace("service.py", "Reconnecting to previous VPN " + getVPNLastConnectedProfile())
                                        debugTrace("Not connected, reconnecting to " + getVPNLastConnectedProfile())
                                        setVPNRequestedProfile(getVPNLastConnectedProfile())
                                        setVPNRequestedProfileFriendly(getVPNLastConnectedProfileFriendly())
                                        setVPNLastConnectedProfile("")
                                        setVPNLastConnectedProfileFriendly("")
                                        reconnect_vpn = True
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
                                            writeVPNConfiguration(getVPNProfile())
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


            # Connect or disconnect in response to an API call
            api_command = getAPICommand()
            if vpn_setup and not api_command == "":
                addon = xbmcaddon.Addon()
                infoTrace("service.py", "API command found, " + api_command)
                if api_command == "Disconnect":
                    setVPNRequestedProfile(api_command)
                    setVPNRequestedProfileFriendly(api_command)
                    reconnect_vpn = True
                elif api_command == "Cycle":
                    requestVPNCycle(True)
                    # Preload some cycle variables to force cycle to activate immediately
                    last_cycle = getVPNCycle()
                    cycle_timer = 9
                elif api_command == "Fake":
                    fakeItTillYouMakeIt(True)
                elif api_command == "Real":
                    fakeItTillYouMakeIt(False)
                elif api_command == "Pause":
                    setVPNMonitorState("Stopped")
                    addon.setSetting("monitor_paused", "true")
                elif api_command == "Restart":
                    setVPNMonitorState("Started")
                    addon.setSetting("monitor_paused", "false")
                elif api_command == "Reconnect":
                    forceReconnect("True")
                elif api_command == "GetIP":
                    updateIPInfo(addon)
                else:
                    # Connect command is basically the profile name...any errors will 
                    # be filtered in the api.py code before the command is passed to here
                    setVPNRequestedProfile(api_command)
                    setVPNRequestedProfileFriendly(getFriendlyProfileName(api_command))
                    reconnect_vpn = True
                updateAPITimer()
                clearAPICommand()

                        
            # See if the addon is requesting to cycle through the VPNs
            cycle_requested = getVPNCycle()
            if vpn_setup and not cycle_requested == "":

                # Wait a short period, and then just grab the lock anyway.
                forceCycleLock()
                debugTrace("Got forced cycle lock in cycle part of service, cycle is " + cycle_requested)
                
                # Reset the timer if this is a different request than last time we looked
                if not cycle_requested == last_cycle:
                    debugTrace("New Cycling VPN connection " + cycle_requested)
                    last_cycle = cycle_requested
                    cycle_timer = 0
                
                # Increment cycle counter so that user has the chance to cycle multiple times before connection
                cycle_timer = cycle_timer + delay

                # Let's connect!  cycle_timer of > 7 assumes at least 2 cycles of 4 seconds so a 10 second-ish de-bounce
                if cycle_timer > 7:
                    debugTrace("Running VPN cycle request " + cycle_requested + ", current VPN is " + getVPNProfile())
                    if not (cycle_requested == "Disconnect" and getVPNProfile() == "") and (not cycle_requested == getVPNProfile()):
                        # A reconnect request is the profile name prefixed with an explanation mark
                        # Need to force a reconnect by pretending it's not currently got a connection
                        if cycle_requested.startswith("!"): 
                            cycle_requested = cycle_requested[1:]
                            setVPNProfile("")
                            setVPNProfileFriendly("")
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
                        if fakeConnection():
                            icon = "/resources/faked.png"
                        else:
                            icon = "/resources/connected.png"
                        if not checkForVPNUpdates(getVPNLocation(addon.getSetting("vpn_provider_validated")), True):
                            notification_title = addon_name
                        else:
                            notification_title = addon_short + ", update available"
                            icon = "/resources/update.png"
                        addon = xbmcaddon.Addon()
                        if addon.getSetting("display_location_on_connect") == "true":
                            _, ip, country, isp = getIPInfo(addon)
                            xbmcgui.Dialog().notification(notification_title, "Connected to "+ getVPNProfileFriendly() + " via Service Provider " + isp + " in " + country + ". IP is " + ip + ".", getAddonPath(True, icon), 20000, False)
                    clearVPNCycle()
                    cycle_timer = 0
                freeCycleLock()    
                
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
                
                    # Stop any streams playing
                    if player.isPlaying(): 
                        filename = player.getPlayingFile()
                        debugTrace("File " + filename + " is playing")                        
                        if addon.getSetting("vpn_stop_media") == "true":
                            if streaming:
                                infoTrace("service.py", "Stopping " + filename + " to change the VPN connection state")                        
                                player.stop()
                                
                    # Stop any existing VPN
                    debugTrace("Stopping VPN before any new connection attempt")
                    prev_connection = "Unknown"
                    if getVPNState() == "started":
                        prev_connection = getVPNProfile()
                        stopVPNConnection()
                        if getVPNRequestedProfile() == "Disconnect" and addon.getSetting("display_location_on_connect") == "true":
                            _, ip, country, isp = getIPInfo(addon)
                            xbmcgui.Dialog().notification(addon_name, "Disconnected from VPN. Service Provider is " + isp + " in " + country + ". IP is " + ip + ".", getAddonPath(True, "/resources/disconnected.png"), 20000, False)
                        else:
                            xbmcgui.Dialog().notification(addon_name, "Disconnected", getAddonPath(True, "/resources/disconnected.png"), 3000, False)
                        infoTrace("service.py", "Disconnected from VPN")
                    else:
                        # Just incase we're in a weird unknown state, this should clear things up
                        stopVPNConnection()
                        debugTrace("Unconnected state, " + getVPNState() + " so disconnected anyway")
                    
                    timer = 0
                
                    # Don't reconnect if this is a disconnect request, or there is nothing to connect to (primary not set)
                    if not getVPNRequestedProfile() == "Disconnect":
                        if not getVPNRequestedProfile() == "":
                            debugTrace("Connecting to VPN profile " + getVPNRequestedProfile())
                            xbmcgui.Dialog().notification(addon_name, "Connecting to "+ getVPNRequestedProfileFriendly(), getAddonPath(True, "/resources/locked.png"), 10000, False)
                            vpn_provider = addon.getSetting("vpn_provider_validated")
                            # Clear the server name so that the alternative 
                            setVPNURL("")
                            if isAlternative(vpn_provider):
                                # (Re)generate the ovpn file and user credentials based on the latest server settings
                                # These will try and do the right thing with regards to existing files if there's
                                # a problem generating new ones, so don't check returns and report problems below
                                # If previous connection is empty then it means we're being asked to reconnect (otherwise
                                # it would be a connection name or "Unknown").  Reconnects can be problematic so sleep
                                # for 5 seconds before reconnecting
                                if prev_connection == "": xbmc.sleep(5000)
                                getAlternativeLocation(vpn_provider, getVPNRequestedProfileFriendly(), getConnectionErrorCount(), False)
                                writeCredentials(addon)
                                updateVPNFile(getVPNRequestedProfile(), vpn_provider)
                            state = startVPNConnection(getVPNRequestedProfile(), addon)
                            if not state == connection_status.CONNECTED:
                                server_tried = getVPNServer()
                                if state == connection_status.AUTH_FAILED:
                                    # If authentication fails we don't want to try and reconnect
                                    # Everything will get reset below if timer is 0 but we'll make
                                    # like the VPN state is off deliberately to avoid reconnect
                                    xbmcgui.Dialog().notification(addon_name, "Error authenticating with VPN, retry or update credentials.", getAddonPath(True, "/resources/warning.png"), 10000, True)
                                elif state == connection_status.FILE_ERROR:
                                    # If the ovpn file doesn't exist, we shouldn't retry
                                    xbmcgui.Dialog().notification(addon_name, "Error connecting, review log for errors.", getAddonPath(True, "/resources/warning.png"), 10000, True)                             
                                else:
                                    connection_errors = getConnectionErrorCount() + 1
                                    failover_connection = -1
                                    # For alternative connections, we should try a couple of times before failing over as
                                    # it could be that our first choice of server was being precious and the next is fine
                                    if isAlternative(vpn_provider):failover_threshold = 2
                                    else: failover_threshold = 1
                                    if connection_errors == failover_threshold and addon.getSetting("vpn_reconnect_next") == "true":
                                        # See if there's a legitimate next connection to failover to
                                        failover_connection = failoverConnection(addon, getVPNRequestedProfile())
                                    if not failover_connection == -1:
                                        # Failover to next connection if the first connection attempt fails
                                        setVPNRequestedProfile(primary_vpns[failover_connection-1])
                                        setVPNRequestedProfileFriendly(primary_vpns_friendly[failover_connection-1])
                                        infoTrace("service.py", "Trying to failover to another connection, using " + getVPNRequestedProfile())
                                        xbmcgui.Dialog().notification(addon_name, "Error connecting to VPN, failing over to next connection.", getAddonPath(True, "/resources/warning.png"), 10000, True)
                                        connection_retry_time = 5
                                    else:
                                        # No failover
                                        if connection_retry_time == 5: connection_errors = 1
                                        if connection_errors > 9:
                                            if addon.getSetting("vpn_reconnect_reboot") == "true" and connection_errors == 10:
                                                if not xbmcgui.Dialog().yesno(addon_name, "Cannot connect to VPN, rebooting system.\nClick cancel within 30 seconds to abort.", nolabel="Reboot", yeslabel="Cancel", autoclose=30000):
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
                                        if not state == connection_status.CONNECTIVITY_ERROR:
                                            dialog_text = "Error connecting to VPN"
                                        else:
                                            dialog_text = "Bad connectivity with VPN"
                                        dialog_text = dialog_text + ", retrying in " + str((connection_retry_time/60)) + " minutes."
                                        xbmcgui.Dialog().notification(addon_name, dialog_text, getAddonPath(True, "/resources/warning.png"), 10000, True)
                                            
                                    setConnectionErrorCount(connection_errors)
                                    timer = 1
                                # Want to kill any running process if it's not completed successfully
                                stopVPNConnection()
                                if state == connection_status.AUTH_FAILED or state == connection_status.FILE_ERROR:
                                    # Stop any reconnect attempt if there's no point
                                    setVPNState("off")
                                errorTrace("service.py", "VPN connect to " + getVPNRequestedProfile() + " has failed, VPN error was " + str(state))
                                if isAlternative(vpn_provider) and not server_tried == "":
                                    errorTrace("service.py", "Server was " + server_tried)
                                writeVPNConfiguration(getVPNRequestedProfile())
                                writeVPNLog()
                                debugTrace("VPN connection failed, errors count is " + str(connection_errors) + " connection timer is " + str(connection_retry_time))
                            else:
                                notification_time = 5000
                                if ifDebug(): writeVPNConfiguration(getVPNProfile())
                                if ifDebug(): writeVPNLog()
                                if getVPNURL() == "":
                                    setVPNURL(getVPNServerFromFile(getVPNProfile()))
                                if fakeConnection():
                                    icon = "/resources/faked.png"
                                else:
                                    icon = "/resources/connected.png"
                                notification_title = addon_name
                                vpn_provider = getVPNLocation(addon.getSetting("vpn_provider_validated"))
                                if checkForVPNUpdates(vpn_provider, True):
                                    notification_title = addon_short + ", update available"
                                    icon = "/resources/update.png"
                                    notification_time = 8000
                                if isAlternative(vpn_provider):
                                    str_last_time = addon.getSetting("alternative_message_time")
                                    try:
                                        if str_last_time == "": last_time = 1
                                        else: last_time = int(str_last_time)
                                    except:
                                        errorTrace("service.py", "Looked at last message time and found " + str_last_time + ", resetting to 1")
                                        last_time = 1
                                    last_id = addon.getSetting("alternative_message_token")
                                    new_id, new_message = getAlternativeMessages(vpn_provider, last_time, last_id)
                                    if not new_message == "":
                                        xbmcgui.Dialog().ok(addon_name, new_message) 
                                        addon.setSetting("alternative_message_time", str(now()))
                                        addon.setSetting("alternative_message_token", new_id)
                                addon = xbmcaddon.Addon()
                                if isAlternative(vpn_provider):
                                    postConnectAlternative(vpn_provider)
                                if addon.getSetting("display_location_on_connect") == "true":
                                    _, ip, country, isp = getIPInfo(addon)
                                    xbmcgui.Dialog().notification(notification_title, "Connected to "+ getVPNProfileFriendly() + " via Service Provider " + isp + " in " + country + ". IP is " + ip + ".", getAddonPath(True, icon), 20000, False)
                                else:
                                    xbmcgui.Dialog().notification(notification_title, "Connected to "+ getVPNProfileFriendly(), getAddonPath(True, icon), notification_time, False)
                                if isAlternative(vpn_provider) and not getVPNServer() == "":
                                    infoTrace("service.py", "VPN connected to " + getVPNProfileFriendly() + " using " + getVPNServer())
                                else:
                                    infoTrace("service.py", "VPN connected to " + getVPNProfileFriendly())
                        else:
                            errorTrace("service.py", "Asking to connect to a VPN profile that doesn't exist")
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
                
                # Clear any outstanding API that may have come in during the connection
                clearAPICommand()
                
                # Let the cycle code run again
                freeCycleLock()
                
                reconnect_vpn = False
        
        # Take multiple second long naps, checking to see if there are any outstanding CLI commands
        shutdown = False
        stop_vpn = False
        for i in range(0, delay):
            if waitForAbort(1000):
                # Abort was requested while waiting. We should exit
                infoTrace("service.py", "Abort received, shutting down service")
                shutdown = True
                stop_vpn = True
                break
            if monitor.abortRequested():
                # Disable and uninstall events aren't trapped so we need to check the monitor for aborts too
                infoTrace("service.py", "Abort requested, shutting down service")
                shutdown = True
                break
            if not getAPICommand() == "": 
                break
        if shutdown: break
        
        timer = timer + delay
    
    # Work around Kodi 17 bug that starts a service twice in some cases...
    setRunning(False)
    xbmc.sleep(500)
    
    # Stop the VPN connection before exiting as it could be running on a 'normal' PC, not a dedicated box
    if stop_vpn: stopVPNConnection()
