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
#    Shared code fragments used by the VPN Manager for OpenVPN add-on.

import xbmcaddon
import xbmcvfs
import xbmc
import os
import re
import urllib2
import xbmcgui
import xbmc
import glob
import sys
import time
from platform import getVPNLogFilePath, fakeConnection, isVPNTaskRunning, stopVPN9, stopVPN, startVPN, getAddonPath, getSeparator, getUserDataPath
from platform import getVPNConnectionStatus, connection_status, getPlatform, platforms, writeVPNLog, checkVPNInstall, checkVPNCommand
from platform import getPlatformString, checkPlatform, useSudo, getKeyMapsPath, getKeyMapsFileName
from utility import debugTrace, infoTrace, errorTrace, ifDebug, newPrint
from vpnproviders import getVPNLocation, getRegexPattern, getAddonList, provider_display, usesUserKeys, usesSingleKey, gotKeys, checkForGitUpdates
from vpnproviders import ovpnFilesAvailable, ovpnGenerated, fixOVPNFiles, getLocationFiles, removeGeneratedFiles, copyKeyAndCert, populateSupportingFromGit
from vpnproviders import usesPassAuth, cleanPassFiles, isUserDefined, getKeyPass, getKeyPassName, usesKeyPass, writeKeyPass, refreshFromGit
from vpnproviders import setVPNProviderUpdate, setVPNProviderUpdateTime
from ipinfo import getIPInfoFrom, getIPSources, getNextSource, getAutoSource, isAutoSelect, getErrorValue, getIndex
from logbox import popupOpenVPNLog
from userdefined import importWizard


def getIconPath():
    return getAddonPath(True, "/resources/")    
    

def getFilteredProfileList(ovpn_connections, filter, addon):
    # Filter out the profiles that we're not using
    
    apply_filter = True
    # Filter based on protocol type
    if "TCP" in filter:
        filterTCP = "(TCP"
    else:
        filterTCP = "()"
    if "UDP" in filter:
        filterUDP = "(UDP"
    else:
        filterUDP = "()"

    # A TCP and UDP filter will work for the non-user defined ovpn files but for user 
    # defined profiles we should be more relaxed if the user is looking for all protocols
    if "TCP" in filter and "UDP" in filter : apply_filter = False
        
    # Filter out connections already in use.  If we don't wanna filter
    # the primary connections, just pass 'None' in as the addon
    used = []
    if not addon == None:
        i = 1
        # Adjust the 11 below to change conn_max
        while i < 11:
            s = addon.getSetting(str(i) + "_vpn_validated")
            if not s == "" : used.append(s)
            i = i + 1
        
    connections = []
    for connection in ovpn_connections:
        if apply_filter == False or (filterTCP in connection or filterUDP in connection):
            if not connection in used:
                connections.append(connection)                 
    return connections

    
def getFriendlyProfileList(ovpn_connections):
    # Munge a ovpn full path name is something more friendly
    connections = []
    regex_str = getRegexPattern()
    # Deal with some Windows nonsense
    if getPlatform() == platforms.WINDOWS:
        regex_str = regex_str.replace(r"/", r"\\")
    # Produce a compiled pattern and interate around the list of connections
    pattern = re.compile(regex_str)
    for connection in ovpn_connections:
        connections.append(pattern.search(connection).group(1))        
    return connections
    

def getTranslatedProfileList(ovpn_connections, vpn_provider):
    connections = list(ovpn_connections)
    try:
        debugTrace("Opening translate file for " + vpn_provider)
        translate_file = open(getAddonPath(True, vpn_provider + "/TRANSLATE.txt"), 'r')
        debugTrace("Opened translate file for " + vpn_provider)
        translate = translate_file.readlines()
        translate_file.close()
    except Exception as e:
        errorTrace("vpnproviders.py", "Couldn't open the translate file for " + vpn_provider)
        errorTrace("vpnproviders.py", str(e))
        return ovpn_connections
    
    for entry in translate:
        try:
            server, dns = entry.split(",")
            i = connections.index(server)
            connections[i] = dns
        except:
            pass
            
    return connections

    
def getFriendlyProfileName(ovpn_connection):
    # Make the VPN profile names more readable to the user to select from
    regex_str = getRegexPattern()
    # Deal with some Windows nonsense
    if getPlatform() == platforms.WINDOWS:
        regex_str = regex_str.replace(r"/", r"\\")
    # Return friendly version of string
    match = re.search(regex_str, ovpn_connection)
    return match.group(1)
    

def getIPInfo(addon):
    # Generate request to find out where this IP is based
    # Return ip info source, ip, location, isp
    source = addon.getSetting("ip_info_source")
    if (not source in getIPSources()):
        addon.setSetting("ip_info_source", getIPSources()[0])
        source = getIPSources()[0]    
    original_source = source
        
    if isAutoSelect(source):
        source = getAutoSource()

    retry = 0
    bad_response = False
    while retry < 6:
        debugTrace("Getting IP info from " + source)
        start_time = int(time.time())
        ip, country, region, city, isp = getIPInfoFrom(source)
        end_time = int(time.time())
        response_time = end_time - start_time
        debugTrace("Got response, IP is " + ip + " response time in seconds is " + str(response_time))
        if response_time > 60:
            errorTrace("common.py", "Response time from IP info was in excess of a minute (" + str(response_time) + " seconds), check connectivity.")
        
        if ip == "no info":
            # Got a response but couldn't format it.  No point retrying, move to next service or quit
            if isAutoSelect(original_source):
                errorTrace("common.py", "No location information was returned for IP using " + source + ", using next service")
                source = getNextSource(source)
            else:
                errorTrace("common.py", "No location information was returned for IP using " + source)
                break
        elif ip == "error":
            errorTrace("common.py", "Didn't get a good response from "  + source)
            if isAutoSelect(original_source):
                # Only want to retry if this is the first time we've seen an error (recently) otherwise
                # we assume it was broken before and it's still broken now and move to the next
                if getErrorValue(getIndex(source)) > 1:
                    source = getNextSource(source)
                else:
                    debugTrace("Retrying "  + source + ", in 3 seconds")
                    xbmc.sleep(3000)
            else:
                # Only want to retry 2 times if it's not auto select as service is likely broken rather than busy
                if retry == 2: break                    
        else:
            # Worked, exit loop
            break
        retry = retry + 1
        
    # Check to see if the call was good (after 5 retries)
    if ip == "no info" or ip == "error":
        return source, "no info", "unknown", "unknown"

    location = ""
    if not (region == "-" or region == "Not Available"): location = region
    if not (country == "-" or country == "Not Available"):
        if not location == "": location = location + ", "
        location = location + country
    if location == "": location = "Unknown"

    infoTrace("common.py", "Received connection info from "  + source + ", IP " + ip + " location " + location + ", ISP " + isp)
    return source, ip, location, isp

    
def resetVPNConfig(addon, starting):    
    # Reset all of the connection config options
    i = starting
    # Adjust 11 below if changing number of conn_max
    while i < 11:
        addon.setSetting(str(i) + "_vpn_validated", "")
        addon.setSetting(str(i) + "_vpn_validated_friendly", "")
        i = i + 1
    
    
def connectionValidated(addon):
    if not addon.getSetting("1_vpn_validated") == "": return True
    return False


def stopVPNConnection():
    # Kill the running VPN task and reset the current VPN window properties
    debugTrace("Stopping VPN")

    try:
        # End any existing openvpn process
        waiting = True
        i = 0
        while waiting:
            i = i + 1
            
            # Send the kill command to end the openvpn process.
            # After 10 seconds hit it with the -9 hammer
            if i < 20:
                stopVPN()
            else:
                stopVPN9()
        
            # Wait half a second just to make sure the process has time to die
            xbmc.sleep(500)

            # See if the openvpn process is still alive
            if fakeConnection():
                waiting = False
            else:
                waiting = isVPNConnected()
            
            # After 20 seconds something is very wrong (like killall isn't installed...)
            if i > 40: raise RuntimeError("Cannot stop the VPN task after 20 seconds of trying.")
            
        setVPNProfile("")
        setVPNProfileFriendly("")        
        setVPNState("stopped")
        return True
    except Exception as e:
        errorTrace("common.py", "Cannot stop VPN task. Check command to terminate a running task is working.")
        errorTrace("common.py", str(e))
        return False

    
def startVPNConnection(vpn_profile):  
    # Start the VPN, wait for connection, return the result

    startVPN(vpn_profile)
    debugTrace("Waiting for VPN to connect")
    i = 0
    loop_max = 77
    if fakeConnection(): loop_max = 2

    while i <= loop_max:
        xbmc.sleep(2000)
        state = getVPNConnectionStatus()
        if not state == connection_status.UNKNOWN: break
        i = i + 2

    if fakeConnection(): state = connection_status.CONNECTED
    
    if state == connection_status.CONNECTED:
        setVPNProfile(getVPNRequestedProfile())
        setVPNProfileFriendly(getVPNRequestedProfileFriendly())
        setVPNState("started")
        debugTrace("VPN connection to " + getVPNProfile() + " successful")

    return state
    

def isVPNConnected():
    # Return True if the VPN task is still running, or the VPN connection is still active
    # Return False if the VPN task is no longer running and the connection is not active
    
    # If there's no profile, then we're not connected (or should reconnect...)
    if getVPNProfile() == "": return False
    
    # Make a call to the platform routine to detect if the VPN task is running
    return isVPNTaskRunning()
    
    
def setVPNLastConnectedProfile(profile_name):
    # Store full profile path name
    xbmcgui.Window(10000).setProperty("VPN_Manager_Last_Profile_Name", profile_name)
    return

    
def getVPNLastConnectedProfile():
    # Return full profile path name
    return xbmcgui.Window(10000).getProperty("VPN_Manager_Last_Profile_Name")

    
def setVPNLastConnectedProfileFriendly(profile_name):
    # Store shortened profile name
    xbmcgui.Window(10000).setProperty("VPN_Manager_Last_Profile_Friendly_Name", profile_name)
    return 
    
    
def getVPNLastConnectedProfileFriendly():
    # Return shortened profile name
    return xbmcgui.Window(10000).getProperty("VPN_Manager_Last_Profile_Friendly_Name")       
    
    
def setVPNRequestedProfile(profile_name):
    # Store full profile path name
    xbmcgui.Window(10000).setProperty("VPN_Manager_Requested_Profile_Name", profile_name)
    return

    
def getVPNRequestedProfile():
    # Return full profile path name
    return xbmcgui.Window(10000).getProperty("VPN_Manager_Requested_Profile_Name")

    
def setVPNRequestedProfileFriendly(profile_name):
    # Store shortened profile name
    xbmcgui.Window(10000).setProperty("VPN_Manager_Requested_Profile_Friendly_Name", profile_name)
    return 
    
    
def getVPNRequestedProfileFriendly():
    # Return shortened profile name
    return xbmcgui.Window(10000).getProperty("VPN_Manager_Requested_Profile_Friendly_Name")    


def setVPNProfile(profile_name):
    # Store full profile path name
    xbmcgui.Window(10000).setProperty("VPN_Manager_Connected_Profile_Name", profile_name)
    return

    
def getVPNProfile():
    # Return full profile path name
    return xbmcgui.Window(10000).getProperty("VPN_Manager_Connected_Profile_Name")

    
def setVPNProfileFriendly(profile_name):
    # Store shortened profile name
    xbmcgui.Window(10000).setProperty("VPN_Manager_Connected_Profile_Friendly_Name", profile_name)
    return 
    
    
def getVPNProfileFriendly():
    # Return shortened profile name
    return xbmcgui.Window(10000).getProperty("VPN_Manager_Connected_Profile_Friendly_Name")    


def setConnectionErrorCount(count):
    # Return the number of times a connection retry has failed
    xbmcgui.Window(10000).setProperty("VPN_Manager_Connection_Errors", str(count))


def getConnectionErrorCount():
    # Return the number of times a connection retry has failed
    err = xbmcgui.Window(10000).getProperty("VPN_Manager_Connection_Errors")
    if err == "": return 0
    return int(xbmcgui.Window(10000).getProperty("VPN_Manager_Connection_Errors"))

    
def setVPNState(state):
	# Store current state - "off" (deliberately), "stopped", "started", "" (at boot) or "unknown" (error)
    xbmcgui.Window(10000).setProperty("VPN_Manager_VPN_State", state)
    return

    
def getVPNState():
	# Store current state
    return xbmcgui.Window(10000).getProperty("VPN_Manager_VPN_State")


def getSystemData(addon, vpn, network, vpnm, system):
    lines = []
    if vpn:
        site, ip, country, isp = getIPInfo(addon)
        lines.append("[B][COLOR ff0099ff]Connection[/COLOR][/B]")
        if isVPNConnected():
            lines.append("[COLOR ff00ff00]Connected using profile " + getVPNProfileFriendly() + "[/COLOR]")
            lines.append("VPN provider is " + addon.getSetting("vpn_provider"))
        else:
            lines.append("[COLOR ffff0000]Not connected to a VPN[/COLOR]")
        lines.append("Connection location is " + country)
        lines.append("External IP address is " + ip)
        lines.append("Service Provider is " + isp)
        lines.append("Location sourced from " + site)
    if network:
        lines.append("[B][COLOR ff0099ff]Network[/COLOR][/B]")
        lines.append("IP address is " + xbmc.getInfoLabel("Network.IPAddress"))
        lines.append("Gateway is " + xbmc.getInfoLabel("Network.GatewayAddress"))
        lines.append("Subnet mask is " + xbmc.getInfoLabel("Network.SubnetMask"))
        lines.append("Primary DNS is " + xbmc.getInfoLabel("Network.DNS1Address"))
        lines.append("Secondary DNS is " + xbmc.getInfoLabel("Network.DNS2Address"))
    if vpnm:
        lines.append("[B][COLOR ff0099ff]VPN Manager[/COLOR][/B]")
        lines.append("VPN Manager verison is " + addon.getAddonInfo("version"))
        lines.append("VPN Manager behaviour is " + getPlatformString())
        if getPlatform() == platforms.LINUX:
            if useSudo():
                lines.append("VPN Manager is prefixing commands with sudo")
            else:
                lines.append("VPN Manager is not using sudo")
        if isVPNMonitorRunning():
            lines.append("VPN Manager add-on filtering is running")
        else:
            lines.append("VPN Manager add-on filtering is paused")
    if system:
        lines.append("[B][COLOR ff0099ff]System[/COLOR][/B]")
        lines.append("Kodi build version is " + xbmc.getInfoLabel("System.BuildVersion"))
        lines.append("System name is " + xbmc.getInfoLabel("System.FriendlyName"))
        lines.append("System date is " + xbmc.getInfoLabel("System.Date"))
        lines.append("System time is " + xbmc.getInfoLabel("System.Time"))
        lines.append("Platform is " + sys.platform)
        lines.append("Free memory is " + xbmc.getInfoLabel("System.FreeMemory"))
        lines.append("Disk is " + xbmc.getInfoLabel("System.TotalSpace") + ", " + xbmc.getInfoLabel("System.UsedSpace"))
        lines.append("Screen is " + xbmc.getInfoLabel("System.ScreenResolution"))
    return lines


def fixKeymaps():
    # Fix the keymap file name if it's been changed
    name = getKeyMapsFileName()
    dir = getKeyMapsPath(name + "*")
    full_name = getKeyMapsPath(name)
    try:
        debugTrace("Getting contents of keymaps directory " + dir)
        files = (glob.glob(dir))
        files.sort(key=os.path.getmtime)
        if not full_name in files and len(files) > 0:
            # Last file in the list, sorted by modified date gets renamed to the keymap file
            file = files[len(files)-1]
            infoTrace("common.py", "Renaming " + file + " to " + full_name + " as something else has messed with the keymap")
            xbmcvfs.rename(file, full_name)
            xbmc.sleep(100)
            # Wait 10 seconds for rename to happen otherwise quit and let it fail in the future
            for i in range(0, 9):
                if xbmcvfs.exists(full_name): break
                xbmc.sleep(1000)
            return True
    except Exception as e:
        errorTrace("common.py", "Problem fixing the keymap filename.")
        errorTrace("common.py", str(e))
    return False
 

def startService():
    # Routine for config to call to request that service starts.  Can time out if there's no response
    # Check to see if service is not already running (shouldn't be...)
    if not xbmcgui.Window(10000).getProperty("VPN_Manager_Service_Control") == "stopped": return True
    
    debugTrace("Requesting service restarts")
    # Update start property and wait for service to respond or timeout
    xbmcgui.Window(10000).setProperty("VPN_Manager_Service_Control", "start")
    for i in range (0, 30):
        xbmc.sleep(1000)
        if xbmcgui.Window(10000).getProperty("VPN_Manager_Service_Control") == "started": return True
    # No response in 30 seconds, service is probably dead
    errorTrace("common.py", "Couldn't communicate with VPN monitor service, didn't acknowledge a start")
    return False

    
def ackStart():
    # Routine for service to call to acknowledge service has started
    xbmcgui.Window(10000).setProperty("VPN_Manager_Service_Control", "started")

    
def startRequested():
    # Service routine should call this to wait for permission to restart.  
    if xbmcgui.Window(10000).getProperty("VPN_Manager_Service_Control") == "start": return True
    return False

    
def stopService():
    # Routine for config to call to request service stops and waits until that happens
    # Check to see if the service has stopped previously
    if xbmcgui.Window(10000).getProperty("VPN_Manager_Service_Control") == "stopped": return True
    
    debugTrace("Requesting service stops")
    # Update start property and wait for service to respond or timeout
    xbmcgui.Window(10000).setProperty("VPN_Manager_Service_Control", "stop")
    for i in range (0, 30):
        xbmc.sleep(1000)
        if xbmcgui.Window(10000).getProperty("VPN_Manager_Service_Control") == "stopped": return True
    # Haven't had a response in 30 seconds which is badness
    errorTrace("common.py", "Couldn't communicate with VPN monitor service, didn't acknowledge a stop")
    return False

    
def stopRequested():
    # Routine for service to call in order to determine whether to stop
    if xbmcgui.Window(10000).getProperty("VPN_Manager_Service_Control") == "stop": return True
    return False
    
    
def ackStop():    
    # Routine for service to call to acknowledge service has stopped
    xbmcgui.Window(10000).setProperty("VPN_Manager_Service_Control", "stopped")

    
def updateService(reason):
    # Set a windows property to tell the background service to update using the latest config data
    debugTrace("Update service requested " + reason)
    xbmcgui.Window(10000).setProperty("VPN_Manager_Service_Update", "update")

    
def ackUpdate():
    # Acknowledge that the update has been received
    xbmcgui.Window(10000).setProperty("VPN_Manager_Service_Update", "updated")


def forceCycleLock():
    # Loop until we get the lock, or have waited for 10 seconds
    i = 0
    while i < 10 and not xbmcgui.Window(10000).getProperty("VPN_Manager_Cycle_Lock") == "":
        xbmc.sleep(1000)
        i = i + 1
    xbmcgui.Window(10000).setProperty("VPN_Manager_Cycle_Lock", "Forced Locked")
    
    
def getCycleLock():
    # If the lock is forced, don't wait, just return (ie don't queue)
    if xbmcgui.Window(10000).getProperty("VPN_Manager_Cycle_Lock") == "Forced Locked" : return False
    # If there's already a queue on the lock, don't wait, just return
    if not xbmcgui.Window(10000).getProperty("VPN_Manager_Cycle_Lock_Queued") == "" : return False
    # Loop until we get the lock or time out after 5 seconds
    xbmcgui.Window(10000).setProperty("VPN_Manager_Cycle_Lock_Queued", "Queued")
    i = 0
    while i < 5 and not xbmcgui.Window(10000).getProperty("VPN_Manager_Cycle_Lock") == "":
        xbmc.sleep(1000)
        i = i + 1
    # Free the queue so another call can wait on it
    xbmcgui.Window(10000).setProperty("VPN_Manager_Cycle_Lock_Queued", "")   
    # Return false if a forced lock happened whilst we were queuing
    if xbmcgui.Window(10000).getProperty("VPN_Manager_Cycle_Lock") == "Forced Locked" : return False
    # Return false if the lock wasn't obtained because of a time out
    if i == 5 : return False 
    xbmcgui.Window(10000).setProperty("VPN_Manager_Cycle_Lock", "Locked")
    return True

    
def freeCycleLock():
    xbmcgui.Window(10000).setProperty("VPN_Manager_Cycle_Lock", "")
    
    
def updateServiceRequested():
    # Check to see if an update is requred
    return (xbmcgui.Window(10000).getProperty("VPN_Manager_Service_Update") == "update")

    
def requestVPNCycle(immediate):
    # Don't know where this was called from so using plugin name to get addon handle
    addon = xbmcaddon.Addon("service.vpn.manager")
    addon_name = addon.getAddonInfo("name")

    # Don't cycle if we can't get a lock
    if getCycleLock():
    
        # Don't cycle if there's nothing been set up to cycle around
        if connectionValidated(addon):
        
            debugTrace("Got cycle lock in requestVPNCycle")
        
            if addon.getSetting("allow_cycle_disconnect") == "true":
                allow_disconnect = True
            else:
                allow_disconnect = False
            
            # Preload the cycle variable if this is the first time through
            if getVPNCycle() == "":
                if getVPNProfile() == "":
                    setVPNCycle("Disconnect")
                else:
                    setVPNCycle(getVPNProfile())
                next_cycle = immediate
            else:
                next_cycle = True
            
            if next_cycle:
                # Build the list of profiles to cycle through
                profiles=[]
                found_current = False
                if allow_disconnect or ((not allow_disconnect) and getVPNProfile() == ""):
                    profiles.append("Disconnect")
                    if getVPNProfile() == "": found_current = True
                i=1
                # Adjust the 11 below to change conn_max
                while i<11:
                    next_profile = addon.getSetting(str(i)+"_vpn_validated")
                    if not next_profile == "":
                        profiles.append(next_profile)
                        if next_profile == getVPNProfile() : 
                            found_current = True
                    i=i+1
                if not found_current:
                    profiles.append(getVPNProfile())
                      
                # Work out where in the cycle we are and move to the next one
                current_profile = 0
                for profile in profiles:
                    current_profile = current_profile + 1
                    if getVPNCycle() == profile:            
                        if current_profile > (len(profiles)-1):
                            setVPNCycle(profiles[0])
                        else:
                            setVPNCycle(profiles[current_profile])
                        break
              
            # Display a notification message
            icon = getIconPath()+"locked.png"
            notification_title = addon_name
            if getVPNCycle() == "Disconnect":
                if getVPNProfile() == "":
                    dialog_message = "Disconnected"
                    icon = getIconPath()+"disconnected.png"
                else:
                    dialog_message = "Disconnect?"
                    icon = getIconPath()+"unlocked.png"
            else:
                if getVPNProfile() == getVPNCycle():
                    dialog_message = "Connected to " + getFriendlyProfileName(getVPNCycle())
                    if fakeConnection():
                        icon = getIconPath()+"faked.png"
                    else:
                        icon = getIconPath()+"connected.png"
                    if checkForGitUpdates(getVPNLocation(addon.getSetting("vpn_provider_validated")), True):
                        notification_title = "VPN Manager, update available"
                        icon = getIconPath()+"update.png"
                else:
                    dialog_message = "Connect to " + getFriendlyProfileName(getVPNCycle()) + "?"
            
            debugTrace("Cycle request is " + dialog_message)
            xbmcgui.Dialog().notification(notification_title, dialog_message , icon, 3000, False)
        else:
            xbmcgui.Dialog().notification(addon_name, "VPN is not set up and authenticated.", xbmcgui.NOTIFICATION_ERROR, 10000, True)

        freeCycleLock()
        
    
def getVPNCycle():
    return xbmcgui.Window(10000).getProperty("VPN_Manager_Service_Cycle")

    
def setVPNCycle(profile):
    xbmcgui.Window(10000).setProperty("VPN_Manager_Service_Cycle", profile)

    
def clearVPNCycle():
    setVPNCycle("")


def getAPICommand():
    return xbmcgui.Window(10000).getProperty("VPN_Manager_API_Command")

    
def setAPICommand(profile):
    xbmcgui.Window(10000).setProperty("VPN_Manager_API_Command", profile)

    
def clearAPICommand():
    setAPICommand("")
    
    
def isVPNMonitorRunning():
    if xbmcgui.Window(10000).getProperty("VPN_Manager_Monitor_State") == "Started":
        return True
    else:
        return False
    
    
def setVPNMonitorState(state):
    xbmcgui.Window(10000).setProperty("VPN_Manager_Monitor_State", state)
    
    
def getVPNMonitorState():
    return xbmcgui.Window(10000).getProperty("VPN_Manager_Monitor_State")

    
def setConnectTime(addon):
    # Record the connection time
    t = str(int(time.time()))
    addon.setSetting("last_connect_time",t)


def getConnectTime(addon):
    # Get the connection time from the settings or use a default
    t = addon.getSetting("last_connect_time")
    if not t.isdigit():
        # Return the Kodi build time or the time I just wrote this in Feb '17, whichever is more recent
        # Expecting a %m %d %Y format date here but will just grab the year and not do time 
        # formatting because I don't know what Kodi will do to the month in different locales
        seconds = 0
        try:
            build_date = xbmc.getInfoLabel("System.BuildDate")
            seconds = (int(build_date[-4:]) - 1970) * 31557600
        except:
            # In case the formatting of the build date changess
            pass
        vpn_mgr_time = 1487116800
        if seconds < vpn_mgr_time:
            seconds = vpn_mgr_time
        return seconds
    else:
        return int(t)

        
def failoverConnection(addon, current_profile):
    # Given a connection, find it in the list of validated connections and return the next 
    # one in the list, or the first connection if it's the last valid one in the list
    i=1
    found = False
    # Adjust the 11 below to change conn_max
    while i<11:
        next_profile = addon.getSetting(str(i)+"_vpn_validated")
        if not next_profile == "":
            if found: return i
            if next_profile == current_profile: found = True
        else:
            break
        i=i+1
    if found and i>2:
        return 1
    else:
        return -1
        
        
def resetVPNConnections(addon):
    # Reset all connection information so the user is forced to revalidate everything
    infoTrace("resetVPN.py", "Resetting all validated VPN settings and disconnected existing VPN connections")
    
    forceCycleLock()
    
    debugTrace("Stopping any active VPN connections")
    stopVPNConnection()
    
    resetVPNConfig(addon, 1)
    # Remove any last connect settings
    setVPNLastConnectedProfile("")
    setVPNLastConnectedProfileFriendly("")
        
    addon.setSetting("vpn_provider_validated","")    
    
    # Assume no update and force a check when it's connected
    setVPNProviderUpdate("false")
    setVPNProviderUpdateTime(0)
    
    # Removal any password files that were created (they'll get recreated if needed)
    debugTrace("Deleting all pass.txt files")
    cleanPassFiles()
    
    # No need to stop/start monitor, just need to let it know that things have changed.
    # Because this is a reset of the VPN, the monitor should just work out it has no good connections
    updateService("resetVPNConnections")

    freeCycleLock()
    
    xbmcgui.Dialog().notification(addon.getAddonInfo("name"), "Disconnected", getIconPath()+"disconnected.png", 5000, False)
    
    
def disconnectVPN(display_result):
    # Don't know where this was called from so using plugin name to get addon handle
    addon = xbmcaddon.Addon("service.vpn.manager")
    addon_name = addon.getAddonInfo("name")

    debugTrace("Disconnecting the VPN")
    
    forceCycleLock()
    
    # Show a progress box before executing stop
    progress = xbmcgui.DialogProgress()
    progress_title = "Disconnecting from VPN."
    progress.create(addon_name,progress_title)
    
    # Pause the monitor service
    progress_message = "Pausing VPN monitor."
    progress.update(1, progress_title, progress_message)
    if not stopService():
        progress.close()
        # Display error in an ok dialog, user will need to do something...
        errorTrace("common.py", "VPN monitor service is not running, can't stop VPN")
        xbmcgui.Dialog().ok(progress_title, "Error, Service not running.\nCheck log and reboot.")
        freeCycleLock()
        return
    
    xbmc.sleep(500)
    
    progress_message = "Stopping any active VPN connection."
    progress.update(1, progress_title, progress_message)
    
    # Kill the VPN connection if the user hasn't gotten bored waiting
    if not progress.iscanceled():
        stopVPNConnection()
        xbmc.sleep(500)    
        progress_message = "Disconnected from VPN, restarting VPN monitor"
        setVPNLastConnectedProfile("")
        setVPNLastConnectedProfileFriendly("")
        setVPNState("off")
    else:
        progress_message = "Disconnect cancelled, restarting VPN monitor"
        
    # Restart service
    if not startService():
        progress.close()
        errorTrace("common.py", "VPN monitor service is not running, VPN has stopped")
        dialog_message = "Error, Service not running.\nCheck log and reboot."        
    else:
        # Close out the final progress dialog
        progress.update(100, progress_title, progress_message)
        xbmc.sleep(500)
        progress.close()
    
        # Update screen and display result in an ok dialog
        xbmc.executebuiltin('Container.Refresh')
        if display_result:
            _, ip, country, isp = getIPInfo(addon)       
            dialog_message = "Disconnected from VPN.\nNetwork location is " + country + ".\nExternal IP address is " + ip + ".\nService Provider is " + isp
        
        infoTrace("common.py", "Disconnected from the VPN")

    freeCycleLock()
    
    if display_result:
        xbmcgui.Dialog().ok(addon_name, dialog_message)

    
def getCredentialsPath(addon):
    return getAddonPath(True, getVPNLocation(addon.getSetting("vpn_provider"))+"/pass.txt")
    
    
def writeCredentials(addon): 
       
    # Write the credentials file        
    try:
        credentials_path = getCredentialsPath(addon)
        debugTrace("Writing VPN credentials file to " + credentials_path)
        credentials = open(credentials_path,'w')
        credentials.truncate()
        credentials.close()
        credentials = open(credentials_path,'a')
        credentials.write(addon.getSetting("vpn_username")+"\n")
        credentials.write(addon.getSetting("vpn_password")+"\n")
        credentials.close()
    except Exception as e:
        errorTrace("common.py", "Couldn't create credentials file " + credentials_path)
        errorTrace("common.py", str(e))
        return False
    xbmc.sleep(500)
    return True
    

def wizard():
    addon = xbmcaddon.Addon("service.vpn.manager")
    addon_name = addon.getAddonInfo("name")    

    # Indicate the wizard has been run, regardless of if it is to avoid asking again
    addon.setSetting("vpn_wizard_run", "true")
    
    # Wizard or settings?
    if xbmcgui.Dialog().yesno(addon_name, "No primary VPN connection has been set up.  Would you like to do this using the set up wizard or using the Settings dialog?", "", "", "Settings", "Wizard"):
        
        # Select the VPN provider
        provider_list = list(provider_display)
        provider_list.sort()
        vpn = xbmcgui.Dialog().select("Select your VPN provider.", provider_list)
        vpn = provider_display.index(provider_list[vpn])
        vpn_provider = provider_display[vpn]
        
        success = True
        # If User Defined VPN then offer to run the wizard
        if isUserDefined(vpn_provider):
            success = importWizard()        
        
        if success:
            # Get the username and password
            vpn_username = ""
            vpn_password = ""
            if usesPassAuth(vpn_provider):
                vpn_username = xbmcgui.Dialog().input("Enter your " + vpn_provider + " username.", type=xbmcgui.INPUT_ALPHANUM)
                if not vpn_username == "":
                    vpn_password = xbmcgui.Dialog().input("Enter your " + vpn_provider + " password.", type=xbmcgui.INPUT_ALPHANUM, option=xbmcgui.ALPHANUM_HIDE_INPUT)
            
            # Try and connect if we've gotten all the data
            if (not usesPassAuth(vpn_provider)) or (not vpn_password == ""):
                addon.setSetting("vpn_provider", vpn_provider)
                addon.setSetting("vpn_username", vpn_username)
                addon.setSetting("vpn_password", vpn_password)
                connectVPN("1", vpn_provider)
                # Need to reinitialise addon here for some reason...
                addon = xbmcaddon.Addon("service.vpn.manager")
                if connectionValidated(addon):
                    xbmcgui.Dialog().ok(addon_name, "Successfully connected to " + vpn_provider + ".  Use the Settings dialog to add additional VPN connections.  You can also define add-on filters to dynamically change the VPN connection being used.")
                else:
                    xbmcgui.Dialog().ok(addon_name, "Could not connect to " + vpn_provider + ".  Use the Settings dialog to correct any issues and try connecting again.")
                
            else:
                xbmcgui.Dialog().ok(addon_name, "You need to enter both a VPN username and password to connect.")
        else:
            xbmcgui.Dialog().ok(addon_name, "There was a problem setting up the User Defined provider.  Fix any issues and run the wizard again from the VPN Configuration tab.")
            
def removeUsedConnections(addon, connection_order, connections):
    # Filter out any used connections from the list given
    # Don't filter anything if it's not one of the primary connection
    if connection_order == "0": return connections
    unused = []
    for connection in connections:
        i = 1
        found = False
        # Adjust 11 below if changing number of conn_max
        while i < 11:
            if connection == addon.getSetting(str(i) + "_vpn_validated_friendly"):
                found = True
            i = i + 1
        if not found : unused.append(connection)
    return unused

            
def connectVPN(connection_order, vpn_profile):

    # Don't know where this was called from so using plugin name to get addon handle
    addon = xbmcaddon.Addon("service.vpn.manager")
    addon_name = addon.getAddonInfo("name")

    # Check openvpn installed and runs
    if not (addon.getSetting("checked_openvpn") == "true"):
        debugTrace("Checking platform is valid and openvpn is installed")
        if checkPlatform(addon) and checkVPNInstall(addon): addon.setSetting("checked_openvpn", "true")
        else: return
    
    # If we've not arrived here though the addon (because we've used the add-on setting
    # on the option menu), we want to surpress running the wizard as there's no need.
    if not addon.getSetting("vpn_wizard_run") == "true":
        addon.setSetting("vpn_wizard_run", "true")

    if not addon.getSetting("ran_openvpn") == "true":
        debugTrace("Checking openvpn can be run")
        stopVPN9()    
        if checkVPNCommand(addon): addon.setSetting("ran_openvpn", "true")
        else: return
    
    # This is needed because after a default it can end up as a null value rather than one of 
    # the three selections.  If it's null, just force it to the best setting anyway.
    vpn_protocol = addon.getSetting("vpn_protocol")
    if not ("UDP" in vpn_protocol or "TCP" in vpn_protocol):
        errorTrace("common.py", "VPN protocol is dodgy (" + vpn_protocol + ") resetting it to UDP")
        addon.setSetting("vpn_protocol", "UDP")
        vpn_protocol = "UDP"
    
    # Do some stuff to set up text used in dialog windows
    connection_title = ""
    
    # Adjust strings below if changing number of conn_max
    if connection_order == "0" : connection_title = ""
    if connection_order == "1" : connection_title = " first"
    if connection_order == "2" : connection_title = " second"
    if connection_order == "3" : connection_title = " third"
    if connection_order == "4" : connection_title = " fourth"
    if connection_order == "5" : connection_title = " fifth"
    if connection_order == "6" : connection_title = " sixth"
    if connection_order == "7" : connection_title = " seventh"
    if connection_order == "8" : connection_title = " eighth"
    if connection_order == "9" : connection_title = " ninth"
    if connection_order == "10" : connection_title = " tenth"
    
    state = ""
    got_keys = True
    got_key_pass = True
    keys_copied = True
    cancel_attempt = False
    cancel_clear = False
    
    forceCycleLock()
    
    # Display a progress dialog box (put this on the screen quickly before doing other stuff)
    progress = xbmcgui.DialogProgress()
    progress_title = "Connecting to" + connection_title + " VPN."
    progress.create(addon_name,progress_title) 

    debugTrace(progress_title)
        
    # Pause the monitor service
    progress_message = "Pausing VPN monitor."
    progress.update(1, progress_title, progress_message)
    xbmc.sleep(500)
    
    if not stopService():
        progress.close()
        # Display error result in an ok dialog
        errorTrace("common.py", "VPN monitor service is not running, can't start VPN")
        xbmcgui.Dialog().ok(progress_title, "Error, Service not running.\nCheck log and re-enable.")
        return

    if not progress.iscanceled():
        progress_message = "VPN monitor paused."
        debugTrace(progress_message)
        progress.update(3, progress_title, progress_message)
        xbmc.sleep(500)
        
    # Stop any active VPN connection
    if not progress.iscanceled():
        progress_message = "Stopping any active VPN connection."    
        progress.update(5, progress_title, progress_message)
        stopVPNConnection()

    if not progress.iscanceled():
        progress_message = "Disconnected from VPN."
        progress.update(6, progress_title, progress_message)
        xbmc.sleep(500)

    vpn_provider = getVPNLocation(addon.getSetting("vpn_provider"))
        
    # Check to see if there are new ovpn files
    provider_download = True
    reset_connections = False
    if not progress.iscanceled() and not isUserDefined(vpn_provider):
        progress_message = "Checking for latest provider files."
        progress.update(7, progress_title, progress_message)
        xbmc.sleep(500)
        if checkForGitUpdates(vpn_provider, False):
            addon = xbmcaddon.Addon("service.vpn.manager")
            if (connection_order == "1" and addon.getSetting("2_vpn_validated") == ""):
                # Is this provider able to update via the interweb?
                provider_download = refreshFromGit(vpn_provider, progress)    
            else:
                progress_message = "New VPN provider files found! Click OK to download and reset existing settings. [I]If you use existing settings they may not continue to work.[/I]"
                if not xbmcgui.Dialog().yesno(progress_title, progress_message, "", "", "OK", "Use Existing"):
                    provider_download = refreshFromGit(vpn_provider, progress)
                    # This is horrible code to avoid adding more booleans.  It'll pretend that the files
                    # didn't download and skip to the end, but it'll indicate that connections need resetting
                    if provider_download == True:
                        progress_title = "Downloaded new VPN provider files"
                        reset_connections = True
                        provider_download = False
                else:
                    progress_message = "[I]VPN provider updates are available, but using existing settings.[/I]"
                    progress.update(7, progress_title, progress_message)
                    xbmc.sleep(2000)
        else:
            progress_message = "Using latest VPN provider files."
            progress.update(7, progress_title, progress_message)
            xbmc.sleep(500)
        addon = xbmcaddon.Addon("service.vpn.manager") 
        
    # Install the VPN provider    
    existing_connection = ""
    if not progress.iscanceled() and provider_download:
        # This is some code to copy the user name from a default file rather than use the user entered values.
        # It exists to help development where swapping between providers constantly is tedious.
        default_path = getUserDataPath(getVPNLocation(vpn_provider) + "/DEFAULT.txt")
        if connection_order == "1" and xbmcvfs.exists(default_path):
            default_file = open(default_path, 'r')
            default = default_file.readlines()
            default_file.close()
            if len(default) == 2:
                default_value = default[0].strip(' \t\n\r')
                addon.setSetting("vpn_username", default_value)
                default_value = default[1].strip(' \t\n\r')
                addon.setSetting("vpn_password", default_value)  
            else:
                errorTrace("common.py", "DEFAULT.txt found in VPN directory for " + vpn_provider + ", but file appears to be invalid.")

        # Reset the username/password if it's not being used
        if not usesPassAuth(getVPNLocation(vpn_provider)):
            addon.setSetting("vpn_username", "")
            addon.setSetting("vpn_password", "")  
                
        vpn_username = addon.getSetting("vpn_username")
        vpn_password = addon.getSetting("vpn_password")
        
        # Reset the setting indicating we've a good configuration for just this connection
        if not connection_order == "0":
            existing_connection = addon.getSetting(connection_order + "_vpn_validated")
            addon.setSetting(connection_order + "_vpn_validated", "")
            addon.setSetting(connection_order + "_vpn_validated_friendly", "")
        last_provider = addon.getSetting("vpn_provider_validated")
        last_credentials = addon.getSetting("vpn_username_validated") + " " + addon.getSetting("vpn_password_validated")
        if last_provider == "" : last_provider = "?"
        
        # Provider or credentials we've used previously have changed so we need to reset all validated connections
        vpn_credentials = vpn_username + " " + vpn_password
        if not last_provider == vpn_provider:
            last_credentials = "?"
        if not last_credentials == vpn_credentials:
            debugTrace("Credentials have changed since last time through so need to revalidate")
            resetVPNConfig(addon, 1)   
       
    # Generate or fix the OVPN files if we've not done this previously
    provider_gen = False
    if not progress.iscanceled() and provider_download:
        provider_gen = True
        if not ovpnFilesAvailable(getVPNLocation(vpn_provider)):
            # Generate the location files if this is a provider which uses generated file
            
            # Clear generated files
            removeGeneratedFiles()
            
            # Copy non-ovpn files (ovpn files will be copied as they're fixed)
            if populateSupportingFromGit(getVPNLocation(vpn_provider)):
                
                # Fetch the list of locations available.  If there are multiple, the user can select
                locations = getLocationFiles(getVPNLocation(vpn_provider))            
                default_label = "Default"
                i = 0            
                for location in locations:
                    locations[i] = location[location.index("LOCATIONS")+10:location.index(".txt")]
                    if locations[i] == "" : locations[i] = default_label
                    i = i + 1
            else:
                provider_gen = False

            if provider_gen:
                cancel_text = "[I]Cancel connection attempt[/I]"
                selected_profile = ""
                
                if len(locations) == 0 and not isUserDefined(vpn_provider) and ovpnGenerated(getVPNLocation(vpn_provider)):
                    errorTrace("common.py", "No LOCATIONS.txt files found in VPN directory.  Cannot generate ovpn files for " + vpn_provider + ".")
                if len(locations) > 1:
                    # Add the cancel option to the dialog box list
                    locations.append(cancel_text)
                    selected_location = xbmcgui.Dialog().select("Select connections profile", locations)
                    selected_profile = locations[selected_location]
                    if selected_profile == default_label : selected_profile = ""
                
                if not selected_profile == cancel_text:
                    addon.setSetting("vpn_locations_list", selected_profile)
                    progress_message = "Setting up VPN provider " + vpn_provider + " (please wait)."
                    progress.update(11, progress_title, progress_message)
                    # Delete any old files in other directories
                    debugTrace("Deleting all generated ovpn files")
                    # Generate new ones
                    try:
                        provider_gen = fixOVPNFiles(getVPNLocation(vpn_provider), selected_profile)
                    except Exception as e:
                        errorTrace("common.py", "Couldn't generate new .ovpn files")
                        errorTrace("common.py", str(e))
                        provider_gen = False
                    xbmc.sleep(500)
                else:
                    # User selected cancel on dialog box
                    provider_gen = False
                    cancel_attempt = True
        addon = xbmcaddon.Addon("service.vpn.manager")
 
                    
    if provider_gen:
        if not progress.iscanceled():
            progress_message = "Using VPN provider " + vpn_provider + "."
            progress.update(15, progress_title, progress_message)
            xbmc.sleep(500)
                            
        # Set up user credentials file
        if (not progress.iscanceled()) and usesPassAuth(getVPNLocation(vpn_provider)):
            credentials_path = getCredentialsPath(addon)
            debugTrace("Attempting to use the credentials in " + credentials_path)
            if (not last_credentials == vpn_credentials) or (not xbmcvfs.exists(credentials_path)) or (not connectionValidated(addon)):
                progress_message = "Configuring authentication settings for user " + vpn_username + "."
                progress.update(16, progress_title, progress_message)
                provider_gen = writeCredentials(addon)

    if provider_gen:
        ovpn_name = ""
        if not progress.iscanceled():
            if usesPassAuth(getVPNLocation(vpn_provider)):
                progress_message = "Using authentication settings for user " + vpn_username + "."
            else:
                progress_message = "User authentication not used with " + vpn_provider + "."
            progress.update(19, progress_title, progress_message)
            xbmc.sleep(500)

        # Display the list of connections
        if not progress.iscanceled():

            if not connection_order == "0":
                switch = True
                if addon.getSetting("location_ip_view") == "true": ip_view = True
                else: ip_view = False
                # Build ths list of connections and the server/IP alternative
                all_connections = getAddonList(vpn_provider, "*.ovpn")
                ovpn_connections = getFilteredProfileList(all_connections, vpn_protocol, addon)
                if len(ovpn_connections) == 0: errorTrace("common.py", "No .ovpn files found for filter " + vpn_protocol + ".")
                none_filter = "UDP and TCP"
                # If there are no connections, reset the filter to show everything and try again
                if len(ovpn_connections) == 0 and isUserDefined(vpn_provider):
                    infoTrace("common.py", "Removing protocol filter and retrying.")
                    addon.setSetting("vpn_protocol", none_filter)
                    vpn_protocol = addon.getSetting("vpn_protocol")
                    ovpn_connections = getFilteredProfileList(all_connections, vpn_protocol, addon)
                ovpn_connections.sort()
                location_connections = getFriendlyProfileList(ovpn_connections)
                if existing_connection == "":
                    cancel_text = "[I]Cancel connection attempt[/I]"
                else:
                    cancel_text = "[I]Cancel connection attempt and clear connection[/I]"
                    cancel_clear = True
                location_connections.append(cancel_text)
                switch_text =  "[I]Switch between location and server views[/I]"
                location_connections.insert(0, switch_text)
                ip_connections = getTranslatedProfileList(location_connections, getVPNLocation(vpn_provider))
                
                while switch:
                    debugTrace("Displaying list of connections with filter " + vpn_protocol)
                    if ip_view:
                        connections = ip_connections
                    else:
                        connections = location_connections

                    selected_connection = xbmcgui.Dialog().select("Select " + connection_title + " VPN profile", connections)                  
                
                    # Based on the value selected, get the path name to the ovpn file
                    ovpn_name = connections[selected_connection]
                    if ovpn_name == cancel_text:
                        ovpn_name = ""
                        cancel_attempt = True
                        break
                    elif ovpn_name == switch_text:
                        if ip_view: 
                            ip_view = False
                            addon.setSetting("location_ip_view", "false")
                        else: 
                            ip_view = True
                            addon.setSetting("location_ip_view", "true")
                    else:
                        # Have to get the right connection name and allow for the switch line in the array
                        ovpn_connection = ovpn_connections[selected_connection - 1]
                        ovpn_name = getFriendlyProfileName(ovpn_connection)
                        break
            else:
                ovpn_name = getFriendlyProfileName(vpn_profile)
                ovpn_connection = vpn_profile

        if (not progress.iscanceled()) and (not ovpn_name == ""):
            # Fetch the key from the user if one is needed
            if usesUserKeys(getVPNLocation(vpn_provider)):                
                # If a key already exists, skip asking for it
                if not (gotKeys(getVPNLocation(vpn_provider), ovpn_name)):
                    # Stick out a helpful message if this is first time through
                    if not gotKeys(getVPNLocation(vpn_provider), ""):
                        xbmcgui.Dialog().ok(addon_name, vpn_provider + " requires key and certificate files unique to you in order to authenticate.  These are typically called [I]client.key and client.crt[/I] or [I]user.key and user.crt[/I] or can be embedded within [I].ovpn[/I] files.")
                        
                    # Get the last directory browsed to avoid starting from the top
                    start_dir = xbmcgui.Window(10000).getProperty("VPN_Manager_User_Directory")
                    if usesSingleKey(getVPNLocation(vpn_provider)): 
                        xbmcgui.Dialog().ok(addon_name, vpn_provider + " uses the same key and certificate for all connections. Make either the .key and .crt, or the a .ovpn file available on an accessable drive or USB key.")
                        select_title = "Select key or ovpn for all connections"
                    else: 
                        xbmcgui.Dialog().ok(addon_name, vpn_provider + " uses a different key and certificate for each connection.  Make either the .key and .cert or .ovpn [COLOR red]relevant to your selected connection[/COLOR] available on an accessable drive or USB key.")
                        select_title = "Select key or ovpn for " + ovpn_name
                    key_file = xbmcgui.Dialog().browse(1, select_title, "files", ".key|.ovpn", False, False, start_dir + getSeparator(), False)
                    if key_file.endswith(".key") or key_file.endswith(".ovpn"):
                        start_dir = os.path.dirname(key_file)
                        if usesSingleKey(getVPNLocation(vpn_provider)): select_title = "Select the certificate for all connections"
                        else: select_title = "Select cert for " + ovpn_name
                        if key_file.endswith(".key"):
                            crt_file = xbmcgui.Dialog().browse(1, select_title, "files", ".crt", False, False, start_dir + getSeparator(), False)
                        else:
                            # If an ovpn file was selected, let's assume the key and the cert are in there
                            # The user can always separate them out themselves if this is wrong
                            crt_file = key_file
                        if crt_file.endswith(".crt") or crt_file.endswith(".ovpn"):
                            start_dir = os.path.dirname(crt_file)
                            xbmcgui.Window(10000).setProperty("VPN_Manager_User_Directory", start_dir)
                            keys_copied = copyKeyAndCert(getVPNLocation(vpn_provider), ovpn_name, key_file, crt_file)
                            got_keys = keys_copied
                        else:
                            got_keys = False
                    else:
                        got_keys = False

            if usesKeyPass(getVPNLocation(vpn_provider)) and got_keys:
                key_pass_file = getUserDataPath(getVPNLocation(vpn_provider) + "/" + getKeyPassName(getVPNLocation(vpn_provider), ovpn_name))
                key_password = getKeyPass(key_pass_file)
                if key_password == "":
                    key_password = xbmcgui.Dialog().input("Enter the password for your user key", "", xbmcgui.INPUT_ALPHANUM)
                    if key_password == "": got_key_pass = False
                    else: 
                        if not writeKeyPass(key_pass_file, key_password):
                            got_key_pass = False
            
        # Try and connect to the VPN provider using the entered credentials        
        if (not progress.iscanceled()) and (not ovpn_name == "") and got_keys and got_key_pass:    
            progress_message = "Connecting using profile " + ovpn_name + "."
            debugTrace(progress_message)
            
            # Start the connection and wait a second before starting to check the state
            startVPN(ovpn_connection)
            
            i = 0
            # Bad network takes over a minute to spot so loop for a bit longer (each loop is 2 seconds)
            loop_max = 37
            if fakeConnection(): loop_max = 2
            percent = 20
            while i <= loop_max:
                progress.update(percent, progress_title, progress_message)
                xbmc.sleep(2000)
                state = getVPNConnectionStatus()
                if not (state == connection_status.UNKNOWN or state == connection_status.TIMEOUT) : break
                if progress.iscanceled(): break
                i = i + 1
                percent = percent + 2

    # Mess with the state to make it look as if we've connected to a VPN
    if fakeConnection() and not progress.iscanceled() and provider_gen and not ovpn_name == "" and got_keys and got_key_pass: state = connection_status.CONNECTED
    
    log_option = True
    # Determine what happened during the connection attempt        
    if state == connection_status.CONNECTED :
        # Success, VPN connected! Display an updated progress window whilst we work out where we're connected to
        progress_message = "Connected, checking location info."
        progress.update(96, progress_title, progress_message)
        _, ip, country, isp = getIPInfo(addon)
        # Indicate we're restarting the VPN monitor
        progress_message = "Connected, restarting VPN Monitor"
        progress.update(98, progress_title, progress_message)
        xbmc.sleep(500)
        # Set up final message
        progress_message = "Connected, VPN monitor restarted."
        if fakeConnection():
            dialog_message = "Faked connection to a VPN in " + country + ".\nUsing profile " + ovpn_name + ".\nExternal IP address is " + ip + ".\nService Provider is " + isp + "."
        else:
            dialog_message = "Connected to a VPN in " + country + ".\nUsing profile " + ovpn_name + ".\nExternal IP address is " + ip + ".\nService Provider is " + isp + "."
        infoTrace("common.py", dialog_message)
        if ifDebug(): writeVPNLog()
        # Store that setup has been validated and the credentials used
        setVPNProfile(ovpn_connection)
        setVPNProfileFriendly(ovpn_name)
        if not connection_order == "0":
            addon.setSetting("vpn_provider_validated", vpn_provider)
            addon.setSetting("vpn_username_validated", vpn_username)
            addon.setSetting("vpn_password_validated", vpn_password)
            addon.setSetting(connection_order + "_vpn_validated", ovpn_connection)
            addon.setSetting(connection_order + "_vpn_validated_friendly", ovpn_name)
        setVPNState("started")
        setVPNRequestedProfile("")
        setVPNRequestedProfileFriendly("")
        setVPNLastConnectedProfile("")
        setVPNLastConnectedProfileFriendly("")
        setConnectionErrorCount(0)
        setConnectTime(addon)
        # Indicate to the service that it should update its settings
        updateService("connectVPN")
    elif progress.iscanceled() or cancel_attempt:
        # User pressed cancel.  Don't change any of the settings as we've no idea how far we got
        # down the path of installing the VPN, configuring the credentials or selecting the connection
        # We're assuming here that if the VPN or user ID has been changed, then the connections are invalid
        # already.  If the cancel happens during the connection validation, we can just use the existing one.
        # Surpress the display of the log option on the final dialog
        log_option = False
        # Set the final message to indicate user cancelled operation
        progress_message = "Cancelling connection attempt, restarting VPN monitor."
        progress.update(97, progress_title, progress_message)
        # Set the final message to indicate cancellation
        progress_message = "Cancelling connection attempt, VPN monitor restarted."
        # Restore the previous connection info 
        dialog_message = "Cancelled connection attempt, VPN is disconnected.\n"
        if not connection_order == "0":
            if not isVPNConnected():
                if cancel_clear:
                    dialog_message = dialog_message + "This connection has been removed from the list of valid connections."
                else:
                    dialog_message = dialog_message + "This connection has not been validated."
                resetVPNConfig(addon, int(connection_order))
        else:
            dialog_message = dialog_message + "Please reconnect."
            
        # Don't know how far we got, if we were trying to connect and then got cancelled,
        # there might still be an instance of openvpn running we need to kill
        stopVPN9()
        # We should also stop the service from trying to do a reconnect, if it's confused
        setVPNRequestedProfile("")
        setVPNRequestedProfileFriendly("")
        setVPNLastConnectedProfile("")
        setVPNLastConnectedProfileFriendly("")
        setVPNState("off")
    else:
        # An error occurred, The current connection is already invalidated.  The VPN credentials might 
        # be ok, but if they need re-entering, the user must update them which will force a reset.
        if not reset_connections:
            progress_message = "Error connecting to VPN, restarting VPN monitor."
        else:
            progress_message = "Restarting VPN monitor."
        progress.update(97, progress_title, progress_message)
        xbmc.sleep(500)
        # Set the final message to show an error occurred
        if not reset_connections:
            progress_message = "Error connecting, VPN is disconnected. VPN monitor restarted."
        else:
            progress_message = "VPN monitor restarted"
        # First set of errors happened prior to trying to connect
        if not provider_download:
            if reset_connections:
                dialog_message = "Please revalidate all connections."
            else:
                dialog_message = "Unable to download the VPN provider files. Check log and try again."
            log_option = False
        elif not provider_gen:
            dialog_message = "Error updating .ovpn files or creating user credentials file. Check log to determine cause of failure."
            log_option = False
        elif not got_keys:
            log_option = False
            if not keys_copied:
                if key_file == crt_file:
                    dialog_message = "Failed to extract user key or cert from ovpn file. Check log and opvn file and retry."
                else:
                    dialog_message = "Failed to copy supplied user key and cert files. Check log and retry."
            else:
                dialog_message = "User key and certificate files are required, but were not provided.  Locate the files or an ovpn file that contains them and try again."
        elif not got_key_pass:
            log_option = False
            dialog_message = "A password is needed for the user key, but was not entered. Try and connect again using the user key password."
        elif ovpn_name == "":
            log_option = False
            dialog_message = "No VPN profiles were available for " + vpn_protocol + ". They've all been used or none exist for the selected protocol filter."
        else:
            # This second set of errors happened because we tried to connect and failed
            if state == connection_status.AUTH_FAILED: 
                dialog_message = "Error connecting to VPN, authentication failed. Check your username and password (or cert and key files)."
                credentials_path = getCredentialsPath(addon)
                if not connection_order == "0":
                    addon.setSetting("vpn_username_validated", "")
                    addon.setSetting("vpn_password_validated", "")
            elif state == connection_status.NETWORK_FAILED: 
                dialog_message = "Error connecting to VPN, could not estabilish connection. Check your username, password and network connectivity and retry."
            elif state == connection_status.TIMEOUT:
                dialog_message = "Error connecting to VPN, connection has timed out. Try using a different VPN profile or retry."
            elif state == connection_status.ROUTE_FAILED:
                dialog_message = "Error connecting to VPN, could not update routing table. Retry and then check log."
            elif state == connection_status.ACCESS_DENIED:
                dialog_message = "Error connecting to VPN, could not update routing table. On Windows, Kodi must be run as administrator."
            elif state == connection_status.OPTIONS_ERROR:
                dialog_message = "Error connecting to VPN, unrecognised option. Disable block-outside-dns in debug menu, reset ovpn files and retry. Or check log and review ovpn file in use."
            else:
                dialog_message = "Error connecting to VPN, something unexpected happened.\nRetry to check openvpn operation and then check log."
                addon.setSetting("ran_openvpn", "false")
            
            # Output what when wrong with the VPN to the log
            writeVPNLog()

        if not connection_order == "0" :
            resetVPNConfig(addon, int(connection_order))
        
        errorTrace("common.py", dialog_message)

        # The VPN might be having a spaz still so we want to ensure it's stopped
        stopVPN9()
        # We should also stop the service from trying to do a reconnect, if it's confused
        setVPNRequestedProfile("")
        setVPNRequestedProfileFriendly("")
        setVPNLastConnectedProfile("")
        setVPNLastConnectedProfileFriendly("")
        setVPNState("off")

    # Restart service
    if not startService():
        progress.close()
        errorTrace("common.py", "VPN monitor service is not running, VPN has started")
        dialog_message = "Error, Service not running.\nCheck log and reboot."        
    else:
        # Close out the final progress dialog
        progress.update(100, progress_title, progress_message)
        xbmc.sleep(500)
        progress.close()
    
    freeCycleLock()

    # Display connection result in an ok dialog
    if log_option:
        if xbmcgui.Dialog().yesno(progress_title, dialog_message, "", "", "OK", "VPN Log"):
            popupOpenVPNLog(getVPNLocation(vpn_provider))
    else:
        xbmcgui.Dialog().ok(progress_title, dialog_message)
    
    # Refresh the screen if this is not being done on settings screen
    if connection_order == "0" : xbmc.executebuiltin('Container.Refresh')
    

  