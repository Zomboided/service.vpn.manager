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
#    Shared code fragments used by the add-on.

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
from vpnplatform import getVPNLogFilePath, fakeConnection, isVPNTaskRunning, stopVPN9, stopVPN, startVPN, getAddonPath, getSeparator, getUserDataPath
from vpnplatform import getVPNConnectionStatus, connection_status, getPlatform, platforms, writeVPNLog, checkVPNInstall, checkVPNCommand, checkKillallCommand
from vpnplatform import getPlatformString, checkPlatform, useSudo, getKeyMapsPath, getKeyMapsFileName, getOldKeyMapsFileName, checkPidofCommand
from utility import debugTrace, infoTrace, errorTrace, ifDebug, newPrint, getID, getName, getShort, isCustom, getCustom
from vpnproviders import getVPNLocation, getRegexPattern, getAddonList, provider_display, usesUserKeys, usesSingleKey, gotKeys, checkForVPNUpdates
from vpnproviders import ovpnFilesAvailable, ovpnGenerated, fixOVPNFiles, getLocationFiles, removeGeneratedFiles, copyKeyAndCert, populateSupportingFromGit
from vpnproviders import usesPassAuth, cleanPassFiles, isUserDefined, getKeyPass, getKeyPassName, usesKeyPass, writeKeyPass, refreshVPNFiles
from vpnproviders import setVPNProviderUpdate, setVPNProviderUpdateTime, getVPNDisplay, isAlternative, allowViewSelection, updateVPNFile
from vpnproviders import getAlternativePreFetch, getAlternativeFriendlyLocations, getAlternativeFriendlyServers, getAlternativeLocation, getAlternativeServer
from vpnproviders import authenticateAlternative, getAlternativeUserPass, getAlternativeProfiles, allowReconnection, postConnectAlternative
from ipinfo import getIPInfoFrom, getIPSources, getNextSource, getAutoSource, isAutoSelect, getErrorValue, getIndex
from logbox import popupOpenVPNLog
from access import setVPNURL, getVPNURL, getVPNProfile
from userdefined import importWizard


DIALOG_SPEED = 500


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

    
def getFriendlyProfileList(ovpn_connections, highlight, colour):
    # Munge a ovpn full path name is something more friendly
    connections = []
    regex_str = getRegexPattern()
    # Deal with some Windows nonsense
    if getPlatform() == platforms.WINDOWS:
        regex_str = regex_str.replace(r"/", r"\\")
    # Produce a compiled pattern and interate around the list of connections
    pattern = re.compile(regex_str)
    for connection in ovpn_connections:
        if highlight == connection and not colour == "":
            connections.append("[COLOR " + colour + "]" + pattern.search(connection).group(1) + "[/COLOR]")
        else:
            connections.append(pattern.search(connection).group(1))        
    return connections


def getAlternativeFriendlyProfileList(ovpn_connections, highlight, colour):
    # Format the active connection
    connections = []
    for connection in ovpn_connections:
        if not highlight == "" and highlight in connection and not colour == "":
            connections.append("[COLOR " + colour + "]" + connection + "[/COLOR]")
        else:
            connections.append(connection)
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
        errorTrace("common.py", "Couldn't open the translate file for " + vpn_provider)
        errorTrace("common.py", str(e))
        return ovpn_connections
    
    for entry in translate:
        try:
            server, dns = entry.split(",")
            i = connections.index(server)
            connections[i] = dns
        except:
            pass
            
    return connections


def getValidatedList(addon, exclude):
    # Return all of the validated conncetions
    connections = []
    # Adjust 11 below if changing number of conn_max
    i = 1
    while i < 11:
        connection = addon.getSetting(str(i) + "_vpn_validated")
        if not connection == "" and not connection == exclude:
            connections.append(connection)
        i = i + 1
    return connections
    
    
def getFriendlyProfileName(ovpn_connection):
    # Make the VPN profile names more readable to the user to select from
    regex_str = getRegexPattern()
    # Deal with some Windows nonsense
    if getPlatform() == platforms.WINDOWS:
        regex_str = regex_str.replace(r"/", r"\\")
    # Return friendly version of string
    match = re.search(regex_str, ovpn_connection)
    try:
        return match.group(1)
    except Exception as e:
        errorTrace("common.py", "Failed to find a friendly name for " + ovpn_connection)
        errorTrace("common.py", str(e))
        raise
    
    
def getVPNServerFromFile(ovpn_name):
    # Extract the server from the ovpn file
    try:
        debugTrace("Opening ovpn file to get server name " + ovpn_name)
        ovpn_file = open((ovpn_name), 'r')
        ovpn = ovpn_file.readlines()
        ovpn_file.close()
    except Exception as e:
        errorTrace("common.py", "Couldn't open the ovpn file " + ovpn_name)
        errorTrace("common.py", str(e))
        return ""
    
    for param in ovpn:
        if param.startswith("remote"):
            param = param.strip(" \n")
            remote_params = param.split()
            if len(remote_params) > 1:
                return remote_params[1]
    
    errorTrace("common.py", "Couldn't find a server in the ovpn file " + ovpn_name)
    return ""
    
    
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
    services_used = 1
    while retry < 6:
        debugTrace("Getting IP info from " + source)
        start_time = int(time.time())
        ip, country, region, city, isp = getIPInfoFrom(source)
        end_time = int(time.time())
        response_time = end_time - start_time
        debugTrace("Got response, IP is " + ip + ", response time in seconds is " + str(response_time))

        if ip == "no info":
            # Got a response but couldn't format it.  No point retrying, move to next service or quit
            if isAutoSelect(original_source):
                errorTrace("common.py", "No location information was returned for IP using " + source + ", using next service")
                source = getNextSource(source)
            else:
                errorTrace("common.py", "No location information was returned for IP using " + source)
                break
        elif ip == "error" or ip == "no response":
            errorTrace("common.py", "Didn't get a good response from "  + source)
            if isAutoSelect(original_source):
                # Only want to retry if this is the first time we've seen an error (recently) otherwise
                # we assume it was broken before and it's still broken now and move to the next
                if getErrorValue(getIndex(source)) > 1:
                    source = getNextSource(source)
                    if ip == "no response": services_used += 1
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
    if ip == "no info" or ip == "error" or ip == "no response":
        if services_used > 3:
            errorTrace("common.py", "All services failed with no response, could be a DNS issue")
        return "", "no info", "unknown", "unknown"

    location = ""
    if not (region == "-" or region == "Not Available"): location = region
    if not (country == "-" or country == "Not Available"):
        if not location == "": location = location + ", "
        location = location + country
    if location == "": location = "Unknown"

    # Have to dumb down the trace string to ASCII to avoid errors caused by foreign characters
    trace_text = "Received connection info from "  + source + ", IP " + ip + " location " + location + ", ISP " + isp
    trace_text = trace_text.encode('ascii', 'ignore')
    infoTrace("common.py", trace_text)
    
    return source, ip, location, isp

    
def resetVPNConfig(addon, starting):    
    # Reset all of the connection config options
    i = starting
    # Adjust 11 below if changing number of conn_max
    while i < 11:
        addon.setSetting(str(i) + "_vpn_validated", "")
        addon.setSetting(str(i) + "_vpn_validated_friendly", "")
        # Kodi18 bug, remove this condition if the use of the same ID multiple times is fixed
        if i == 1: addon.setSetting("vpn_validated", "false")
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
            # Try it again after 5 seconds if it's still not stopped
            if i == 1 or i == 10:
                stopVPN()
            # Send the big daddy kill after 10 seconds
            if i == 20:
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
        setVPNURL("")
        setVPNState("stopped")
        setConnectChange()
        return True
    except Exception as e:
        errorTrace("common.py", "Cannot stop VPN task. Check command to terminate a running task is working.")
        errorTrace("common.py", str(e))
        return False

    
def startVPNConnection(vpn_profile, addon):  
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
        state = connectivityTest(addon)
        
    if state == connection_status.CONNECTED:
        setVPNProfile(getVPNRequestedProfile())
        setVPNProfileFriendly(getVPNRequestedProfileFriendly())        
        setVPNState("started")
        setConnectTime(addon)
        setConnectChange()
        debugTrace("VPN connection to " + getVPNProfile() + " successful")

    return state
    

def connectivityTest(addon):
    # Use the function to determine where the external location is to estabilish whether there's connectivity
    if not addon.getSetting("vpn_connectivity_test") == "true": return connection_status.CONNECTED
    debugTrace("Checking network connectivity")
    source, ip, country, isp = getIPInfo(addon)
    if source == "": 
        errorTrace("common.py", "VPN connected but could not verify location so it's likely there's a connectivity or DNS issue")
        return connection_status.CONNECTIVITY_ERROR
    else:
        return connection_status.CONNECTED
    
    
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
    # Update the server name if this is a connection
    if not profile_name == "":
        setVPNServer(profile_name)
        setVPNRequestedServer("")
    else:
        setVPNServer("")
    return

    
def setVPNProfileFriendly(profile_name):
    # Store shortened profile name
    xbmcgui.Window(10000).setProperty("VPN_Manager_Connected_Profile_Friendly_Name", profile_name)
    return 
    
    
def getVPNProfileFriendly():
    # Return shortened profile name
    return xbmcgui.Window(10000).getProperty("VPN_Manager_Connected_Profile_Friendly_Name")    

    
def setVPNServer(server_name):
    # Store server name
    xbmcgui.Window(10000).setProperty("VPN_Manager_Connected_Server_Name", server_name)
    return

    
def getVPNServer():
    # Return server name
    return xbmcgui.Window(10000).getProperty("VPN_Manager_Connected_Server_Name")


def setVPNRequestedServer(server_name):
    # Store server name
    xbmcgui.Window(10000).setProperty("VPN_Manager_Requested_Server_Name", server_name)
    return

    
def getVPNRequestedServer():
    # Return server name
    return xbmcgui.Window(10000).getProperty("VPN_Manager_Requested_Server_Name")    
    
    
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
        lines.append("[B][COLOR ff0099ff]Connection[/COLOR][/B]")
        site, ip, country, isp = getIPInfo(addon)
        if isVPNConnected(): 
            lines.append("[COLOR ff00ff00]Connected using profile " + getVPNProfileFriendly() + "[/COLOR]")
            lines.append("VPN provider is " + addon.getSetting("vpn_provider"))
            server = getVPNURL()
            if not server == "": lines.append("Server is " + server)
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
        sdns = xbmc.getInfoLabel("Network.DNS2Address")
        if not sdns == "": lines.append("Secondary DNS is " + sdns)
    if vpnm:
        lines.append("[B][COLOR ff0099ff]" + getShort() + "[/COLOR][/B]")
        lines.append(getShort() + " verison is " + addon.getAddonInfo("version"))
        lines.append(getShort() + " behaviour is " + getPlatformString())
        if getPlatform() == platforms.LINUX:
            if useSudo():
                lines.append(getShort() + " is prefixing commands with sudo")
            else:
                lines.append(getShort() + " is not using sudo")
        if isVPNMonitorRunning():
            lines.append(getShort() + " add-on filtering is running")
        else:
            lines.append(getShort() + " add-on filtering is paused")
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
    # Fix the keymap file name if it's been changed or the old name was being used
    name = getKeyMapsFileName()
    old = getOldKeyMapsFileName()
    dir = getKeyMapsPath("*")
    full_name = getKeyMapsPath(name)
    try:
        debugTrace("Getting contents of keymaps directory " + dir)
        files = (glob.glob(dir))
        if not full_name in files and len(files) > 0:
            for file in files:
                if (name in file) or (old in file):
                    infoTrace("common.py", "Renaming " + file + " to " + full_name)
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

 
def clearServiceState():
    # Clear the service state during initialisation.  It can get funky on an upgrade
	xbmcgui.Window(10000).setProperty("VPN_Manager_Service_Control", "start")


def startService():
    # Routine for config to call to request that service starts.  Can time out if there's no response
    
    # Return true if the check should be bypassed
    if xbmcgui.Window(10000).getProperty("VPN_Manager_Service_Control") == "ignore": return True
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
    
    # Return true if the check should be bypassed
    if xbmcgui.Window(10000).getProperty("VPN_Manager_Service_Control") == "ignore": return True
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


def suspendStartStop():
    # This will stop any service checking from happening and return the current state
    current = xbmcgui.Window(10000).getProperty("VPN_Manager_Service_Control")
    xbmcgui.Window(10000).setProperty("VPN_Manager_Service_Control", "ignore")
    return current    
    
    
def resumeStartStop(state):
    # This can be used to resume service checking, returning to a previous known state (or pass in an empty string)
    xbmcgui.Window(10000).setProperty("VPN_Manager_Service_Control", state)    
    
    
def suspendConfigUpdate():
    # This will stop any config updates from happening
    xbmcgui.Window(10000).setProperty("VPN_Manager_Update_Suspend", "true")
    
    
def resumeConfigUpdate():
    # This can be used to resume config updates
    xbmcgui.Window(10000).setProperty("VPN_Manager_Update_Suspend", "")
    updateService("resumeConfigUpdate")

    
def configUpdate():
    return xbmcgui.Window(10000).getProperty("VPN_Manager_Update_Suspend") == ""
    
    
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
    addon = xbmcaddon.Addon(getID())
    addon_name = getName()

    # Don't cycle if we can't get a lock
    if getCycleLock():
    
        # Don't cycle if there's nothing been set up to cycle around
        if connectionValidated(addon):
            debugTrace("Got cycle lock in requestVPNCycle")
            vpn_provider = addon.getSetting("vpn_provider_validated")
        
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
                            if allowReconnection(vpn_provider) or addon.getSetting("allow_cycle_reconnect") == "true":
                                profiles.append("!" + next_profile)
                    i = i + 1
                if not found_current:
                    profiles.append(getVPNProfile())
                    if allowReconnection(vpn_provider) or addon.getSetting("allow_cycle_reconnect") == "true":
                        profiles.append("!" + getVPNProfile())
                      
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
            dialog_message = ""
            
            if getVPNCycle() == "Disconnect":
                if getVPNProfile() == "":
                    dialog_message = "Disconnected"
                    icon = getIconPath()+"disconnected.png"
                else:
                    dialog_message = "Disconnect?"
                    icon = getIconPath()+"unlocked.png"
            else:
                cycle_name = getVPNCycle()
                reconnect = False
                if cycle_name.startswith("!"): 
                    reconnect = True
                    cycle_name = cycle_name[1:]
                friendly_cycle_name = getFriendlyProfileName(cycle_name)
                if not reconnect and getVPNProfile() == cycle_name:
                    if not cycle_name == "": dialog_message = "Connected to " + friendly_cycle_name
                    if fakeConnection():
                        icon = getIconPath()+"faked.png"
                    else:
                        icon = getIconPath()+"connected.png"
                    if checkForVPNUpdates(getVPNLocation(vpn_provider), True):
                        notification_title = getShort() + ", update available"
                        icon = getIconPath()+"update.png"
                else:
                    if not cycle_name == "":
                        if not reconnect: dialog_message = "Connect to " + friendly_cycle_name + "?"
                        else: dialog_message = "Reconnect to " + friendly_cycle_name + "?"
                        
            if not dialog_message == "": 
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
    

def updateAPITimer():
    xbmcgui.Window(10000).setProperty("VPN_Manager_API_Last_Command_Time", str(int(time.time())))
    

def updateIPInfo(addon):
    _, ip, location, isp = getIPInfo(addon)
    connected = "False"
    if isVPNConnected(): connected = "True"
    xbmcgui.Window(10000).setProperty("VPN_Manager_API_State", connected)
    xbmcgui.Window(10000).setProperty("VPN_Manager_API_IP", ip)
    xbmcgui.Window(10000).setProperty("VPN_Manager_API_Location", location)
    xbmcgui.Window(10000).setProperty("VPN_Manager_API_Provider", isp)

    
def forceReconnect(state):
    xbmcgui.Window(10000).setProperty("VPN_Manager_Force_Reconnect", state)

    
def isForceReconnect():
    if xbmcgui.Window(10000).getProperty("VPN_Manager_Force_Reconnect") == "True": return True
    return False      
    
    
def isVPNMonitorRunning():
    if xbmcgui.Window(10000).getProperty("VPN_Manager_Monitor_State") == "Started": return True
    else: return False
    
    
def setVPNMonitorState(state):
    xbmcgui.Window(10000).setProperty("VPN_Manager_Monitor_State", state)
    
    
def getVPNMonitorState():
    return xbmcgui.Window(10000).getProperty("VPN_Manager_Monitor_State")

    
def setConnectTime(addon):
    # Record the connection time
    t = int(time.time())
    addon.setSetting("last_connect_time",str(t))
    setReconnectTime(addon, t)
    
    
def setConnectChange():
    xbmcgui.Window(10000).setProperty("VPN_Manager_Last_Connection_Change", str(int(time.time())))
    
    
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


def setReconnectTime(addon, t):
    reconnect = int(addon.getSetting("auto_reconnect_vpn"))
    if reconnect > 0: 
        reconnect = t + (reconnect * 3600)
        xbmcgui.Window(10000).setProperty("VPN_Manager_Reconnect_Time", str(reconnect))
    else:
        xbmcgui.Window(10000).setProperty("VPN_Manager_Reconnect_Time", "")
    
    
def getReconnectTime():
    t = xbmcgui.Window(10000).getProperty("VPN_Manager_Reconnect_Time")
    if t == "": return 0
    else: return int(t)


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
        i = i + 1
    if found and i>2:
        return 1
    else:
        return -1
        
        
def resetVPNConnections(addon):
    # Reset all connection information so the user is forced to revalidate everything
    infoTrace("common.py", "Resetting all validated VPN settings and disconnected existing VPN connections")
    
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
    
    
def resetVPNProvider(addon):
    # Reset a bunch of provider information to make the user set it up again
    addon.setSetting("vpn_provider_validated", "")
    addon.setSetting("vpn_username_validated", "")
    addon.setSetting("vpn_password_validated", "")
    addon.setSetting("location_server_view", "false")
    addon.setSetting("vpn_locations_list", "")
    addon.setSetting("vpn_wizard_enabled", "true")
    
    
def disconnectVPN(display_result):
    # Don't know where this was called from so using plugin name to get addon handle
    addon = xbmcaddon.Addon(getID())
    addon_name = getName()

    debugTrace("Disconnecting the VPN")
    
    forceCycleLock()
    
    # Show a progress box before executing stop
    progress = xbmcgui.DialogProgress()
    progress_title = "Disconnecting from VPN"
    progress.create(addon_name,progress_title)
    
    # Pause the monitor service
    progress_message = "Pausing VPN monitor..."
    progress.update(1, progress_title, progress_message)
    if not stopService():
        progress.close()
        # Display error in an ok dialog, user will need to do something...
        errorTrace("common.py", "VPN monitor service is not running, can't stop VPN")
        xbmcgui.Dialog().ok(progress_title, "Error, Service not running.  Check log and reboot.")
        freeCycleLock()
        return
    
    xbmc.sleep(DIALOG_SPEED)
    
    progress_message = "Stopping any active VPN connection..."
    progress.update(1, progress_title, progress_message)
    
    # Kill the VPN connection if the user hasn't gotten bored waiting
    if not progress.iscanceled():
        stopVPNConnection()
        xbmc.sleep(DIALOG_SPEED)    
        progress_message = "Disconnected from VPN, restarting VPN monitor..."
        setVPNLastConnectedProfile("")
        setVPNLastConnectedProfileFriendly("")
        setVPNState("off")
    else:
        progress_message = "Disconnect cancelled, restarting VPN monitor..."
    
    dialog_message = ""
    dialog_message_2 = ""
    dialog_message_3 = ""
    # Restart service
    if not startService():
        progress.close()
        errorTrace("common.py", "VPN monitor service is not running, VPN has stopped")
        dialog_message = "Error, Service not running.  Check log and reboot."        
    else:
        # Close out the final progress dialog
        progress.update(100, progress_title, progress_message)
        xbmc.sleep(DIALOG_SPEED)
        progress.close()
    
        # Update screen and display result in an ok dialog
        xbmc.executebuiltin('Container.Refresh')
        if display_result:
            _, ip, country, isp = getIPInfo(addon)
            # Kodi18 bug, these should be one string with a \n between them
            dialog_message = "[B]Disconnected from VPN[/B]"
            dialog_message_2 = "Using " + ip + ", located in " + country
            dialog_message_3 = "Service Provider is " + isp
        
        infoTrace("common.py", "Disconnected from the VPN")

    freeCycleLock()
    
    if display_result:
        xbmcgui.Dialog().ok(addon_name, dialog_message, dialog_message_2, dialog_message_3)

    
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
        vpn_provider = getVPNLocation(addon.getSetting("vpn_provider"))
        if isAlternative(vpn_provider):
            username, password = getAlternativeUserPass(vpn_provider)
        else:
            username = addon.getSetting("vpn_username")
            password = addon.getSetting("vpn_password")
        if not (username == "" or password == ""):
            credentials = open(credentials_path,'a')
            credentials.write(username + "\n")
            credentials.write(password + "\n")
            credentials.close()
        else:
            errorTrace("common.py", "User name or password were not found, couldn't create credentials file " + credentials_path)
            return False
    except Exception as e:
        errorTrace("common.py", "Couldn't create credentials file " + credentials_path)
        errorTrace("common.py", str(e))
        return False
    xbmc.sleep(500)
    return True
    

def wizard():
    addon = xbmcaddon.Addon(getID())
    addon_name = getName()    
    
    debugTrace("Wizard offered, current VPN is " + addon.getSetting("vpn_provider") + ", user is " + addon.getSetting("vpn_username"))
    
    settings = False
    # Wizard or settings?
    if not xbmcgui.Dialog().yesno(addon_name, "A VPN hasn't been set up yet.  Would you like to run the setup wizard or go to the settings?", nolabel="Wizard", yeslabel="Settings"):

        suspendConfigUpdate()
        
        success = True
        debugTrace("Running wizard")    
        # Check everything is installed and working
        if not addon.getSetting("ran_openvpn") == "true":
            if getPlatform() == platforms.WINDOWS:
                xbmcgui.Dialog().ok(addon_name, "This add-on uses OpenVPN to make the VPN connection.  You can download this from openvpn.net.  Click ok to check that openvpn is installed and working.")
                # Don't mess with anything if openvpn can be found using the path in the settings
                if not (addon.getSetting("openvpn_no_path") == "false" and xbmcvfs.exists(addon.getSetting("openvpn_path")+"openvpn.exe")):
                    # Settings aren't valid so look in the default place
                    if xbmcvfs.exists("c:\\Program Files\\OpenVPN\\bin\\openvpn.exe"):
                        addon.setSetting("openvpn_path", "c:\\Program Files\\OpenVPN\\bin\\")
                        addon.setSetting("openvpn_no_path", "false")
                    else:
                        # Last resort default to class path
                        addon.setSetting("openvpn_path", "")
                        addon.setSetting("openvpn_no_path", "true")
            else:
                xbmcgui.Dialog().ok(addon_name, "This add-on uses the openvpn, killall and pidof commands to make and manage the VPN connections.  You will need to install these if your system doesn't have them.  Click ok to set some system defaults and check everything is working.")
                # Same logic as above, check the settings, check the default path and if all else fails, use the class path
                if not (addon.getSetting("openvpn_no_path") == "false" and xbmcvfs.exists(addon.getSetting("openvpn_path")+"openvpn.exe")):
                    if xbmcvfs.exists("/usr/sbin/openvpn"):
                        addon.setSetting("openvpn_path", "/usr/sbin/")
                        addon.setSetting("openvpn_no_path", "false")
                    else:
                        addon.setSetting("openvpn_path", "")
                        addon.setSetting("openvpn_no_path", "true")
                # If this is an LE install, don't need sudo and can use the /run directory for the logs, etc
                if getAddonPath(True, "").startswith("/storage/.kodi/"):
                    addon.setSetting("openvpn_sudo", "false")
                    addon.setSetting("openvpn_log_location", "false")
                else:
                    addon.setSetting("openvpn_sudo", "true")
                    addon.setSetting("openvpn_log_location", "true")

            xbmc.sleep(200)
            progress = xbmcgui.DialogProgress()
            progress_title = "Checking dependencies"
            progress.create(addon_name, progress_title) 
            if getPlatform() == platforms.WINDOWS:
                progress_message = "Checking OpenVPN..."
            else:
                progress_message = "Checking openvpn..."
            progress.update(0, progress_title, progress_message)
            if not checkVPNCommand(addon):
                success = False
            xbmc.sleep(1000)
            if not getPlatform() == platforms.WINDOWS:
                # Removing pidof check because most/all Linux platforms should have it, especially those that can run Kodi
                #progress_message = "Checking pidof..."
                #progress.update(33, progress_title, progress_message)    
                #if not checkPidofCommand(addon):
                #    success = False
                #xbmc.sleep(1000)
                progress_message = "Checking killall..."
                progress.update(50, progress_title, progress_message)  
                if not getPlatform() == platforms.WINDOWS and not checkKillallCommand(addon): 
                    success = False
                xbmc.sleep(1000)

            if success == False:
                progress.close()
                xbmc.sleep(200)
                if getPlatform() == platforms.WINDOWS:
                    # Give the user a chance to locate the openvpn directory
                    if xbmcgui.Dialog().yesno(addon_name, "OpenVPN cannot be found.  If you've already installed it, do you want to locate the OpenVPN\\bin directory?", nolabel="No", yeslabel="Yes"):
                        vpn_path = xbmcgui.Dialog().browseSingle(0, "Locate ..\\OpenVPN\\bin\\", "local", "", False, False, "")
                        if xbmcvfs.exists(vpn_path + "openvpn.exe"):
                            addon.setSetting("openvpn_path", vpn_path)
                            addon.setSetting("openvpn_no_path", "false")
                            success = checkVPNCommand(addon)
                    if success == False:                  
                        xbmcgui.Dialog().ok(addon_name, "OpenVPN must be installed.  Run the wizard again after installing it or review the Windows installation instructions.")
                else:
                    xbmcgui.Dialog().ok(addon_name, "The openvpn, killall and pidof commands must be installed.  Check the log for more details and review the Linux installation instructions.")
            else:
                progress_message = "No problems found"
                progress.update(100, progress_title, progress_message)
                xbmc.sleep(1000)
                progress.close()
                
            if success: addon.setSetting("ran_openvpn", "true")
        
        addon = xbmcaddon.Addon(getID())
        if success:
            # Select the VPN provider
            current = ""
            if not isCustom():
                cancel_text = "[I]Cancel setup[/I]"
                # Build the list of display names and highlight the current one if it's been used previously
                provider_list = list(provider_display)
                provider_list.sort()
                if not addon.getSetting("vpn_username") == "":
                    current = addon.getSetting("vpn_provider")
                    i = provider_list.index(getVPNDisplay(current))
                    provider_list[i] = "[B]" + provider_list[i] + "[/B]"
                provider_list.append(cancel_text)
                vpn = xbmcgui.Dialog().select("Select your VPN provider", provider_list)
                selected = provider_list[vpn]
                if not selected == cancel_text:
                    selected = selected.replace("[B]", "")
                    selected = selected.replace("[/B]", "")
                    i = provider_display.index(selected)
                    vpn_provider = provider_display[i]
                else:
                    vpn_provider = ""
                    success = False
                    xbmcgui.Dialog().ok(addon_name, "Setup canceled.  You can run the wizard again by selecting 'Settings' in the add-on menu.")
            else:
                vpn_provider = addon.getSetting("vpn_custom")
                current = vpn_provider
            
        # If User Defined VPN then offer to run the wizard
        addon = xbmcaddon.Addon(getID())
        if success and isUserDefined(vpn_provider):
            success = importWizard()
            if not success: xbmcgui.Dialog().ok(addon_name, "Setup stopped because it could not import any user files.  You can run the wizard again by selecting 'Settings' in the add-on menu.")
        
        addon = xbmcaddon.Addon(getID())        
        if success:
            # Get the username and password
            if usesPassAuth(vpn_provider):
                # Preload with any existing info if it's the same VPN
                if not current == vpn_provider:
                    vpn_username = ""
                    vpn_password = ""
                else:
                    vpn_username = addon.getSetting("vpn_username")
                    vpn_password = addon.getSetting("vpn_password")            
                # Get the user name
                while True:
                    vpn_username = xbmcgui.Dialog().input("Enter your " + vpn_provider + " user name", vpn_username, type=xbmcgui.INPUT_ALPHANUM)
                    if vpn_username == "":
                        if xbmcgui.Dialog().yesno(addon_name, "You must enter the user name supplied by " + vpn_provider + ".  Try again or cancel setup?", nolabel="Try again", yeslabel="Cancel"):
                            xbmcgui.Dialog().ok(addon_name, "Setup canceled.  You can run the wizard again by selecting 'Settings' in the add-on menu.")
                            success = False
                            break
                    else:
                        break
                        
                if not vpn_username == "":
                    while True:
                        vpn_password = xbmcgui.Dialog().input("Enter your " + vpn_provider + " password", vpn_password, type=xbmcgui.INPUT_ALPHANUM, option=xbmcgui.ALPHANUM_HIDE_INPUT)
                        if vpn_password == "":
                            if xbmcgui.Dialog().yesno(addon_name, "You must enter the password supplied by " + vpn_provider + " for user name " + vpn_username + ".  Try again or cancel setup?", nolabel="Try again", yeslabel="Cancel"):
                                xbmcgui.Dialog().ok(addon_name, "Setup canceled.  You can run the wizard again by selecting 'Settings' in the add-on menu.")
                                success = False
                                break
                        else:
                            break
            else:
                xbmcgui.Dialog().ok(addon_name, vpn_provider + " uses private key and cert authentication.  You'll be asked for these during the connection.")
                vpn_username = ""
                vpn_password = ""
        
        addon = xbmcaddon.Addon(getID())
        if success:
            # Offer to default the common options
            if not xbmcgui.Dialog().yesno(addon_name, "Do you want the VPN to connect at start up and be reconnected if necessary [I](recommended)[/I]?  You can set these options later in the 'Monitor' tab on the 'Settings' screen available in the add-on menu", nolabel="Yes", yeslabel="No"):
                # These options will connect and boot, reconnect during streaming or not playing, and reconnect after filtering
                addon.setSetting("vpn_connect_at_boot", "true")
                addon.setSetting("vpn_reconnect", "true")
                addon.setSetting("vpn_reconnect_while_streaming", "true")
                addon.setSetting("vpn_reconnect_filtering", "true")
                addon.setSetting("vpn_stop_media", "true")
            else:
                # These options will mean that the connection is not automatic and not monitored
                addon.setSetting("vpn_connect_at_boot", "false")
                addon.setSetting("vpn_reconnect", "false")        

        addon = xbmcaddon.Addon(getID())       
        if success:
            # Commit the settings entered and try the connection
            addon.setSetting("vpn_provider", vpn_provider)
            addon.setSetting("vpn_username", vpn_username)
            addon.setSetting("vpn_password", vpn_password)
            if not xbmcgui.Dialog().yesno(addon_name, "Click ok to create a VPN connection to " + vpn_provider + " for user name " + vpn_username + ".  You will be asked which connection or country you want to use during the connection process.", nolabel="Ok", yeslabel="Cancel"):
                connectVPN("1", vpn_provider)
                addon = xbmcaddon.Addon(getID())
                if connectionValidated(addon):
                    xbmcgui.Dialog().ok(addon_name, "The wizard has set up " + vpn_provider + " and has connected to " + addon.getSetting("1_vpn_validated_friendly") + ". This is the primary connection and will be used when Kodi starts.")
                    if not xbmcgui.Dialog().yesno(addon_name, "You can use 'Settings' in the add-on menu to optionally validate additional VPN connections or countries and define filters to automatically change the VPN connection being used with each add-on.  Do this now?", nolabel="Yes", yeslabel="No"):
                        settings = True
                else:
                    xbmcgui.Dialog().ok(addon_name, "Could not connect to " + vpn_provider + ".  Correct any issues that were reported during the connection attempt and run the wizard again by selecting 'Settings' in the add-on menu.")
            else:
                xbmcgui.Dialog().ok(addon_name, "Setup canceled.  You can run the wizard again by selecting 'Settings' in the add-on menu.")
                
        resumeConfigUpdate()
        
    else:
        settings = True
    
    addon = xbmcaddon.Addon(getID())
    if settings:
        debugTrace("Opening settings, wizard declined")
        command = "Addon.OpenSettings(" + getID() + ")"
        xbmc.executebuiltin(command)


def dnsFix():
    addon = xbmcaddon.Addon(getID())
    addon_name = getName()
    
    if getPlatform() == platforms.LINUX:
        vpn_provider = addon.getSetting("vpn_provider")
        if not xbmcgui.Dialog().yesno(addon_name, "Do you want to apply or remove the potential DNS fix for " + vpn_provider + "?", nolabel="Apply", yeslabel="Remove"):
            if xbmcgui.Dialog().yesno(addon_name, "Applying this fix will [I]attempt[/I] to fix any DNS issues that you might be experiencing.  [COLOR red]You should not do this if you're not having any connection problems![/COLOR]", nolabel="Cancel", yeslabel="Continue"):
                infoTrace("common.py", "Creating a new APPEND.txt for " + vpn_provider + " to try and fix DNS issues")
                files = False
                # Rename any existing APPEND.txt
                append_path = getUserDataPath(getVPNLocation(vpn_provider) + "/APPEND.txt")
                if xbmcvfs.exists(append_path):
                    files = True
                    append_old = append_path.replace("APPEND.txt", "APPEND.old")
                    debugTrace("Renaming existing APPEND.txt file to " + append_old)
                    try:
                        # Never over write the back up...the DNS wizard could be run a bunch of times and constantly
                        # over writing the back up will mean there is no back up of any user originated file
                        if not xbmcvfs.exists(append_old):
                            xbmcvfs.rename(append_path, append_old)
                        else:
                            debugTrace("Didn't rename existing APPEND.txt as a backup already exists")
                    except Exception as e:
                        errorTrace("common.py", "Couldn't rename " + append_path + " to " + append_old)
                        errorTrace("common.py", str(e))
                        
                # Remove or rename any existing user defined TEMPLATE.txt file            
                template_path = getUserDataPath(getVPNLocation(vpn_provider) + "/TEMPLATE.txt")
                if xbmcvfs.exists(template_path):
                    files = True
                    template_old = template_path.replace("TEMPLATE.txt", "TEMPLATE.old")
                    debugTrace("Renaming existing TEMPLATE.txt file to " + template_old)
                    try:
                        # Never over write the back up
                        if not xbmcvfs.exists(template_old):
                            xbmcvfs.rename(template_path, template_old)
                        else:
                            debugTrace("Couldn't rename, but still need to delete the template to avoid it conflicting with the DNS fix")
                            xbmcvfs.delete(template_path)
                    except Exception as e:
                        errorTrace("common.py", "Couldn't delete " + template_path + " or rename it to " + template_old)
                        errorTrace("common.py", str(e))
                        xbmcgui.Dialog().ok(addon_name, "Unexpected errors were found when attempting to fix DNS issues.  See the log for more details.")
                        return
                
                # Write out the new APPEND.txt file
                errors = False
                try:
                    append_dir = getUserDataPath(getVPNLocation(vpn_provider) + "/")
                    if not xbmcvfs.exists(append_dir):
                        debugTrace("Creating user data directory " + append_dir)
                        append_dir = getUserDataPath(getVPNLocation(vpn_provider))
                        xbmcvfs.mkdir(append_dir)
                    debugTrace("Writing new APPEND.txt file to " + append_path)
                    append_file = open(append_path, 'w')
                    all_paths = []
                    all_paths.append("/etc/openvpn/update-systemd-resolved")
                    all_paths.append("/etc/openvpn/scripts/update-systemd-resolved")
                    all_paths.append(getUserDataPath("update-systemd-resolved"))
                    all_paths.append(getUserDataPath("update-resolv-conf"))
                    all_paths.append("/etc/openvpn/update-resolv-conf")
                    path = ""
                    for try_path in all_paths:
                        if xbmcvfs.exists(try_path):
                            path = try_path
                        if xbmcvfs.exists(try_path + ".sh"):
                            path = try_path + ".sh"
                        if not path == "":
                            debugTrace("Found " + path + " to use as the up and down script")
                            break
                    if "update-resolv-conf" in path:
                        infoTrace("common.py", "Found " + path + " and will call it when the connection goes up and down")
                        append_file.write("dhcp-option DNSSEC allow-downgrade\n")
                        append_file.write("dhcp-option DOMAIN-ROUTE .\n")
                        append_file.write("script-security 2\n")
                        append_file.write("setenv PATH /usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\n")
                        append_file.write("up " + path + "\n")
                        append_file.write("down " + path + "\n")
                        append_file.write("down-pre\n")
                    elif "update-systemd-resolved" in path:
                        infoTrace("common.py", "Found update-systemd-resolved and will call it when the connection goes up and down")
                        append_file.write("dhcp-option DOMAIN-ROUTE .\n")
                        append_file.write("script-security 2\n")
                        append_file.write("setenv PATH /usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\n")
                        append_file.write("up " + path + "\n")
                        append_file.write("down " + path + "\n")
                        append_file.write("down-pre\n")
                    else:
                        errorTrace("common.py", "To attempt a DNS fix, you need to install update-resolv-conf script in /etc/openvpn")
                        errorTrace("common.py", "For systemd enabled installations including LibreELEC, install update-systemd-resolved in /etc/openvpn or /etc/openvpn/scripts")
                        errorTrace("common.py", "Alternatively, you can place either of these scripts in " + getUserDataPath(""))
                        errorTrace("common.py", "Ensure the script you want to use has the right permissions set")
                        errorTrace("common.py", "After installation of one of the scripts, apply the DNS fix again.")
                        errors = True
                    append_file.close()
                except Exception as e:
                    errorTrace("common.py", "Couldn't open or update " + append_path)
                    errorTrace("common.py", str(e))
                    xbmcgui.Dialog().ok(addon_name, "Unexpected errors were found when attempting to fix DNS issues.  See the log for more details.")
                    return
                
                # Update settings to avoid up/down scripts being used
                settings = False
                if not errors:
                    if addon.getSetting("up_down_script") == "true" or addon.getSetting("use_default_up_down") == "true":
                        settings = True
                        addon.setSetting("up_down_script", "false")
                        addon.setSetting("use_default_up_down", "false")
                
                if not errors:
                    if xbmcgui.Dialog().yesno(addon_name, "A [I]potential[/I] fix has been created.  You should now use the [B]Reset VPN Provider[/B] option in the [B]Utilities[/B] tab to apply the fix, and then use the [B]VPN Connections[/B] tab to validate a connection.", nolabel="Ok", yeslabel="Details"):
                        t = ""
                        if settings: t = t + "The OpenVPN up and down script options have been turned off.  "
                        if files: t = t + "Existing user defined TEMPLATE.txt and APPEND.txt files for " + vpn_provider + " have been disabled.  "
                        if t == "" : t = "A new user defined APPEND.txt has been created.  No other changes were necessary."
                        else: t = t + "A new user defined APPEND.txt has been created."
                        xbmcgui.Dialog().ok(addon_name, t)
                    if not isCustom(): xbmcgui.Dialog().ok(addon_name, "If you still have issues after applying this [I]potential[/I] fix, refer to the [B]Trouble Shooting[/B] page found on the [B]GitHub service.vpn.manager wiki.[/B]")
                    else: xbmcgui.Dialog().ok(addon_name, "If you still have issues after applying the [I]potential[/I] fix, refer to your VPN provider support documentation.")
                else:
                    if not isCustom(): xbmcgui.Dialog().ok(addon_name, "[I]A DNS fix was not possible because the required DNS resolution scripts are not available.[/I]  Refer to the Kodi log and the [B]Trouble Shooting[/B] page found on the GitHub service.vpn.manager wiki.")
                    else: xbmcgui.Dialog().ok(addon_name, "[I]A DNS fix was not possible because the required DNS resolution scripts are not available.[/I]  Refer to the Kodi log and your VPN provider support documentation.")
                    try:
                        if xbmcvfs.exists(append_path):
                            xbmcvfs.delete(append_path)
                    except Exception as e:
                        errorTrace("common.py", "Couldn't remove " + append_path)
                        errorTrace("common.py", str(e))
        else:
            append_path = getUserDataPath(getVPNLocation(vpn_provider) + "/APPEND.txt")
            if xbmcvfs.exists(append_path):
                try:
                    xbmcvfs.delete(append_path)
                    infoTrace("common.py", "Removing the APPEND.txt for " + vpn_provider)
                    xbmcgui.Dialog().ok(addon_name, "The potential DNS fix has been removed for " + vpn_provider + ".  You should now use the [B]Reset VPN Provider[/B] option in the [B]Utilities[/B] tab to avoid using the fix with future connections.")
                except Exception as e:
                    errorTrace("common.py", "Couldn't remove " + append_path)
                    errorTrace("common.py", str(e))
                    xbmcgui.Dialog().ok(addon_name, "Unexpected errors were found when attempting remove the DNS fix for " + vpn_provider + ".  See the log for more details.")
            else: xbmcgui.Dialog().ok(addon_name, "No potential DNS fix has been applied to " + vpn_provider + ".")

            
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

            
def checkDirectory(vpn_provider):
    # Check that the directory for the VPN provider exists
    dir_path = getAddonPath(True, getVPNLocation(vpn_provider))
    if xbmcvfs.exists(dir_path): return True
    infoTrace("common.py", "Creating VPN provider directory " + dir_path)
    try:
        xbmcvfs.mkdir(dir_path)
    except Exception as e:
        errorTrace("common.py", "Couldn't create directory " + dir_path)
        errorTrace("common.py", str(e))
        return False
    return True

            
def connectVPN(connection_order, vpn_profile):

    # Don't know where this was called from so using plugin name to get addon handle
    addon = xbmcaddon.Addon(getID())
    addon_name = getName()

    debugTrace("Running connectVPN, connection_order is " + connection_order + ", profile is " + vpn_profile)
    
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

    # Display a progress dialog box (put this on the screen quickly before doing other stuff)
    progress = xbmcgui.DialogProgress()
    progress_title = "Connecting to" + connection_title + " VPN"
    progress.create(addon_name,progress_title)
    debugTrace(progress_title)

    # Check openvpn installed and runs
    if not (addon.getSetting("checked_openvpn") == "true"):
        progress_message = "Checking dependencies..."
        progress.update(1, progress_title, progress_message)
        xbmc.sleep(DIALOG_SPEED)
        debugTrace("Checking platform is valid and openvpn is installed")
        if checkPlatform(addon) and checkVPNInstall(addon): 
            addon.setSetting("checked_openvpn", "true")
        else: 
            progress.close()
            return
  
    if not addon.getSetting("ran_openvpn") == "true":
        progress_message = "Checking dependencies..."
        progress.update(2, progress_title, progress_message)
        xbmc.sleep(DIALOG_SPEED)
        debugTrace("Checking openvpn (and maybe pidof and killall) can be run")
        stopVPN9()    
        if checkVPNCommand(addon) and checkPidofCommand(addon) and checkKillallCommand(addon): 
            addon.setSetting("ran_openvpn", "true")
        else: 
            progress.close()
            return

    # This is needed because after a default it can end up as a null value rather than one of 
    # the three selections.  If it's null, just force it to the best setting anyway.
    vpn_protocol = addon.getSetting("vpn_protocol")
    if not ("UDP" in vpn_protocol or "TCP" in vpn_protocol):
        errorTrace("common.py", "VPN protocol is dodgy (" + vpn_protocol + ") resetting it to UDP")
        addon.setSetting("vpn_protocol", "UDP")
        vpn_protocol = "UDP"
    
    state = ""
    got_keys = True
    got_key_pass = True
    keys_copied = True
    cancel_attempt = False
    cancel_clear = False

    # Pause the monitor service
    progress_message = "Pausing VPN monitor..."
    progress.update(3, progress_title, progress_message)
    xbmc.sleep(DIALOG_SPEED)

    forceCycleLock()
    
    if not stopService():
        progress.close()
        # Display error result in an ok dialog
        errorTrace("common.py", "VPN monitor service is not running, can't start VPN")
        xbmcgui.Dialog().ok(progress_title, "Error, Service not running.\nCheck log and re-enable or reboot.")
        return

    if not progress.iscanceled():
        progress_message = "VPN monitor paused"
        debugTrace(progress_message)
        progress.update(4, progress_title, progress_message)
        xbmc.sleep(DIALOG_SPEED)
        
    # Stop any active VPN connection
    if not progress.iscanceled():
        progress_message = "Stopping any active VPN connection..."    
        progress.update(5, progress_title, progress_message)
        stopVPNConnection()

    if not progress.iscanceled():
        progress_message = "Disconnected from VPN"
        progress.update(6, progress_title, progress_message)
        xbmc.sleep(DIALOG_SPEED)

    if isCustom(): addon.setSetting("vpn_provider", getCustom())
    vpn_provider = getVPNLocation(addon.getSetting("vpn_provider"))
        
    # If the provider has not been validated or has changed, then reset some values
    if not connection_order == "0" and (addon.getSetting("vpn_provider_validated") == "" or not (getVPNLocation(addon.getSetting("vpn_provider_validated")) == vpn_provider)):
        addon.setSetting("location_server_view", "false")
        addon.setSetting("vpn_locations_list", "")
        
    # Check to see if there are new ovpn files
    provider_download = True
    reset_connections = False
    if not progress.iscanceled() and not isUserDefined(vpn_provider):    
        progress_message = "Checking for latest VPN locations..."
        progress.update(7, progress_title, progress_message)
        xbmc.sleep(DIALOG_SPEED)
        if checkForVPNUpdates(vpn_provider, False):
            addon = xbmcaddon.Addon(getID())
            if not connection_order == "0":
                # Offer to download the files if this is part of the validation process
                # If it's an alternative provider, this is dealt with when everything is reset
                if (connection_order == "1" and addon.getSetting("2_vpn_validated") == ""):
                    # Just update if this is the first time a connection is being done
                    provider_download = refreshVPNFiles(vpn_provider, progress)
                else:
                    progress_message = "New VPN locations found! Click OK to download. [I]If you use existing locations they may not continue to work.[/I]"
                    if not xbmcgui.Dialog().yesno(progress_title, progress_message, nolabel="OK", yeslabel="Use Existing"):
                        provider_download = refreshVPNFiles(vpn_provider, progress)
                        # This is horrible code to avoid adding more booleans.  It'll pretend that the files
                        # didn't download and skip to the end, but it'll indicate that connections need resetting
                        if provider_download:
                            progress_title = "Downloaded new VPN files"
                            reset_connections = True
                            provider_download = False
                    else:
                        progress_message = "[I]New VPN locations are available, but using existing locations[/I]"
                        progress.update(7, progress_title, progress_message)
                        xbmc.sleep(3000)
            else:
                progress_message = "[I]New VPN locations found! Update VPN connections to use them. Existing locations may not continue to work.[/I]"
                progress.update(7, progress_title, progress_message)
                xbmc.sleep(5000)
        else:
            progress_message = "Using latest VPN locations"
            progress.update(7, progress_title, progress_message)
            xbmc.sleep(DIALOG_SPEED)
        addon = xbmcaddon.Addon(getID())

        
    # Set up the username and password    
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

        # Reset the user name/password if it's not being used
        if not usesPassAuth(getVPNLocation(vpn_provider)):
            addon.setSetting("vpn_username", "")
            addon.setSetting("vpn_password", "")  
                
        vpn_username = addon.getSetting("vpn_username")
        vpn_password = addon.getSetting("vpn_password")
        # Check for formatting characters first time through
        if connection_order == "1":
            vpn_username_stripped = vpn_username.strip(' \t\n\r')
            if (not vpn_username == vpn_username_stripped) and xbmcgui.Dialog().yesno(progress_title, "Your user name starts or ends with formatting characters (space, tab, new line or return).  Remove them [I](recommended)[/I]?", nolabel="No", yeslabel="Yes"):
                vpn_username = vpn_username_stripped
                addon.setSetting("vpn_username", vpn_username)
            vpn_password_stripped = vpn_password.strip(' \t\n\r')
            if (not vpn_password == vpn_password_stripped) and xbmcgui.Dialog().yesno(progress_title, "Your password starts or ends with formatting characters (space, tab, new line or return).  Remove them [I](recommended)[/I]?", nolabel="No", yeslabel="Yes"):
                vpn_password = vpn_password_stripped
                addon.setSetting("vpn_password", vpn_password)
        
        # Reset the setting indicating we've a good configuration for just this connection
        if not connection_order == "0":
            existing_connection = addon.getSetting(connection_order + "_vpn_validated")
            addon.setSetting(connection_order + "_vpn_validated", "")
            addon.setSetting(connection_order + "_vpn_validated_friendly", "")
            # Kodi18 bug, remove this condition if the use of the same ID multiple times is fixed
            if connection_order == "1": addon.setSetting("vpn_validated", "false")
            
        last_provider = addon.getSetting("vpn_provider_validated")
        last_credentials = addon.getSetting("vpn_username_validated") + " " + addon.getSetting("vpn_password_validated")
        if last_provider == "" : last_provider = "?"
        
        # Provider or credentials we've used previously have changed so we need to reset all validated connections
        vpn_credentials = vpn_username + " " + vpn_password
        if not last_provider == vpn_provider:
            last_credentials = "?"
        if not last_credentials == vpn_credentials:
            debugTrace("Credentials need to be validated")
            resetVPNConfig(addon, 1)
    
    # Check that we can authenticate with the VPN service if neccessary
    if not progress.iscanceled() and provider_download and isAlternative(vpn_provider):
        progress_message = "Authenticating user ID and password for " + vpn_username + "..."
        progress.update(7, progress_title, progress_message)
        # Reuse the provider_download to avoid more variables.  It's not used for alternative connections
        provider_download = authenticateAlternative(vpn_provider, vpn_username, vpn_password)
    
    # Generate or fix the OVPN files if we've not done this previously
    provider_gen = False
    select_location = False
    if not progress.iscanceled() and provider_download:
        provider_gen = checkDirectory(vpn_provider)
        if provider_gen:
            if not isAlternative(vpn_provider):
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
                            select_location = True
                            addon.setSetting("vpn_locations_list", selected_profile)
                            progress_message = "Setting up VPN provider " + vpn_provider + " (please wait)..."
                            progress.update(11, progress_title, progress_message)
                            debugTrace("Deleting all generated ovpn files")
                            # Generate new ones
                            try:
                                provider_gen = fixOVPNFiles(getVPNLocation(vpn_provider), selected_profile)
                                progress_message = "Set up " + vpn_provider
                                progress.update(15, progress_title, progress_message)
                                xbmc.sleep(DIALOG_SPEED)
                            except Exception as e:
                                errorTrace("common.py", "Couldn't generate new .ovpn files")
                                errorTrace("common.py", str(e))
                                provider_gen = False
                            xbmc.sleep(DIALOG_SPEED)
                        else:
                            # User selected cancel on dialog box
                            provider_gen = False
                            cancel_attempt = True
            else:
                # Offer a list of profiles on the first connection attempt
                # We'll use the same profile for all subsequent attempts
                if connection_order == "1" and addon.getSetting("vpn_locations_list") == "":
                    selections, alias, title_text = getAlternativeProfiles(vpn_provider)
                    selected_profile = ""
                    cancel_text = "[I]Cancel connection attempt[/I]"
                    if not len(selections) == 0:
                        if len(selections) == 1:
                            selected_profile = alias[0]
                            debugTrace("Using account " + selected_profile + " as there was only one option")
                        else:
                            selections.append(cancel_text)
                            alias.append(cancel_text)
                            profile_index = xbmcgui.Dialog().select(title_text, selections)
                            selected_profile = alias[profile_index]
                            debugTrace("Using account " + selected_profile)
                    if not selected_profile == cancel_text:
                        select_location = True
                        addon.setSetting("vpn_locations_list", selected_profile)
                        provider_gen = getAlternativePreFetch(vpn_provider)
                    else:
                        # User selected cancel on dialog box
                        provider_gen = False
                        cancel_attempt = True
    
    addon = xbmcaddon.Addon(getID())                
    if provider_gen:                            
        # Set up user credentials file
        if (not progress.iscanceled()) and usesPassAuth(getVPNLocation(vpn_provider)):
            credentials_path = getCredentialsPath(addon)
            debugTrace("Attempting to use the credentials in " + credentials_path)
            if (not last_credentials == vpn_credentials) or (not xbmcvfs.exists(credentials_path)) or (not connectionValidated(addon)):
                progress_message = "Storing authentication settings for user " + vpn_username + "..."
                progress.update(16, progress_title, progress_message)
                provider_gen = writeCredentials(addon)
                xbmc.sleep(DIALOG_SPEED)
    
    if provider_gen:
        ovpn_name = ""

        # Display the list of connections
        if not progress.iscanceled():
            
            # Clear the server in use so it can be set by one of the alternative calls
            # or can be fetched from the ovpn after the ovpn has been chosen and created
            setVPNURL("")
            
            if addon.getSetting("location_server_view") == "true": server_view = True
            else: server_view = False
            if not connection_order == "0":
                switch = True
                # Build ths list of connections and the server/IP alternative
                if not isAlternative(vpn_provider):
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
                    location_connections = getFriendlyProfileList(ovpn_connections, "", "")
                    server_connections = getTranslatedProfileList(location_connections, getVPNLocation(vpn_provider))
                else:
                    location_connections = getAlternativeFriendlyLocations(vpn_provider, True)
                    server_connections = getAlternativeFriendlyServers(vpn_provider, True)
                
                switch_offset = 0
                if allowViewSelection(vpn_provider):
                    switch_text = "[I]Switch between location and server views[/I]"
                    location_connections.insert(0, switch_text)
                    server_connections.insert(0, switch_text)
                    switch_offset = 1
                else:
                    switch_text = ""
                if existing_connection == "":
                    cancel_text = "[I]Cancel connection attempt[/I]"
                else:
                    cancel_text = "[I]Cancel connection attempt and clear connection[/I]"
                    cancel_clear = True
                location_connections.append(cancel_text)
                server_connections.append(cancel_text)
                
                while switch:
                    debugTrace("Displaying list of connections with filter " + vpn_protocol)
                    if server_view:
                        connections = server_connections
                    else:
                        connections = location_connections

                    selected_connection = xbmcgui.Dialog().select("Select " + connection_title + " VPN profile", connections)                  
                    
                    # Based on the value selected, get the path name to the ovpn file
                    selected_name = connections[selected_connection]

                    if selected_name == cancel_text:
                        ovpn_name = ""
                        cancel_attempt = True
                        break
                    elif allowViewSelection(vpn_provider) and selected_name == switch_text:
                        if server_view: 
                            server_view = False
                            addon.setSetting("location_server_view", "false")
                        else: 
                            server_view = True
                            addon.setSetting("location_server_view", "true")
                    else:
                        if not isAlternative(vpn_provider):
                            # Have to get the right connection name and allow for the switch line in the array
                            ovpn_connection = ovpn_connections[selected_connection - switch_offset]
                            ovpn_name = getFriendlyProfileName(ovpn_connection)
                            break
                        else:
                            selected_name = selected_name.strip(" ")
                            progress_message = "Getting profile for " + selected_name + "..."
                            progress.update(18, progress_title, progress_message)
                            if server_view:
                                ovpn_name, ovpn_connection, user_text, ignore = getAlternativeServer(vpn_provider, selected_name, 0, False)
                            else:
                                ovpn_name, ovpn_connection, user_text, ignore = getAlternativeLocation(vpn_provider, selected_name, 0, False)
                            if not ovpn_name == "": 
                                writeCredentials(addon)
                                provider_gen, _, _, _, _ = updateVPNFile(ovpn_connection, vpn_provider)
                                break
                            else:
                                # If there's no location, then user_text might contain a user message to display.
                                # If it doesn't then something bad has happened identifying a location to use
                                if not user_text == "" and not ignore: 
                                    # Display the text and then loop.  The user can cancel if there's a problem
                                    xbmcgui.Dialog().ok(addon_name, user_text)                                    
                                else:
                                    # If there's not a location then continue, letting the rest
                                    # of the code report an error to the user later on
                                    if not ignore: break
            else:
                if not isAlternative(vpn_provider):
                    ovpn_name = getFriendlyProfileName(vpn_profile)
                    ovpn_connection = vpn_profile
                else:
                    # Get the friendly and ovpn names.  If the server view is active then it's up to the
                    # alternative provider code as to whether it returns a readable name or a URL/address
                    if server_view:
                        ovpn_name, ovpn_connection, _, _ = getAlternativeServer(vpn_provider, getFriendlyProfileName(vpn_profile), 0, False)
                    else:
                        ovpn_name, ovpn_connection, _, _ = getAlternativeLocation(vpn_provider, getFriendlyProfileName(vpn_profile), 0, False)
                    if not ovpn_name == "": 
                        writeCredentials(addon)
                        provider_gen, _, _, _, _ = updateVPNFile(ovpn_connection, vpn_provider)
            
            # Get the server name from the ovpn if it's not been filled in already
            if getVPNURL() == "" and not ovpn_name == "" :
                setVPNURL(getVPNServerFromFile(ovpn_connection))
        
        addon = xbmcaddon.Addon(getID())        
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
            progress_message = "Connecting using profile " + ovpn_name + "..."
            debugTrace(progress_message)
            
            # Start the connection and wait a second before starting to check the state
            # There's no retry logic here as a working server would have been selected just before trying
            # to connect.  A subsequent retry will see a different server selected if the previous one failed.
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
    
    addon = xbmcaddon.Addon(getID())
    log_option = True
    dns_error = False
    # Determine what happened during the connection attempt        
    if state == connection_status.CONNECTED:
        # Success, VPN connected! Display an updated progress window whilst we work out where we're connected to
        progress_message = "Connected, checking location info..."
        progress.update(96, progress_title, progress_message)
        source, ip, country, isp = getIPInfo(addon)
        # Indicate we're restarting the VPN monitor
        progress_message = "Connected, restarting VPN monitor..."
        progress.update(98, progress_title, progress_message)
        xbmc.sleep(DIALOG_SPEED)
        # Set up final message
        progress_message = "Connected, VPN monitor restarted"
        server = ""
        # Display the server if enhanced server info is switched on
        if addon.getSetting("vpn_server_info") == "true":
            server = getVPNURL()
        if not server == "": server = "\nServer is " + server + "\n"
        else: server = "\n"
        if fakeConnection():
            dialog_message = "[B]Faked connection to a VPN[/B]\nProfile is " + ovpn_name + server + "Using " + ip + ", located in " + country + "\nService Provider is " + isp
        else:
            # If a VPN location service can't be found, change the message
            if source == "":
                dialog_message = "[B]Connected to a VPN[/B]\nProfile is " + ovpn_name + ", but either there's a DNS issue or some other network problems. You may not be able to access other internet resources until you fix this."
                dns_error = True
            else:
                dialog_message = "[B]Connected to a VPN[/B]\nProfile is " + ovpn_name + server + "Using " + ip + ", located in " + country + "\nService Provider is " + isp
        # Have to dumb down the trace string to ASCII to avoid errors caused by foreign characters
        trace_message = dialog_message.encode('ascii', 'ignore')
        infoTrace("common.py", trace_message)
        if ifDebug(): writeVPNLog()
        # Store that setup has been validated and the credentials used
        setVPNProfile(ovpn_connection)
        setVPNProfileFriendly(ovpn_name)
        if not connection_order == "0":
            addon.setSetting("vpn_provider_validated", vpn_provider)
            addon.setSetting("vpn_username_validated", vpn_username)
            addon.setSetting("vpn_password_validated", vpn_password)
            # Kodi18 bug, remove this line if the use of the same ID multiple times is fixed
            # and change settings.xml back to checking if 1_vpn_validated_friendly is empty
            addon.setSetting("vpn_validated", "true")
            addon.setSetting(connection_order + "_vpn_validated", ovpn_connection)
            addon.setSetting(connection_order + "_vpn_validated_friendly", ovpn_name)
        # Stop the wizard running once the first connection has been validated
        if connection_order == "1":
            addon.setSetting("vpn_wizard_enabled", "false")
        setVPNState("started")
        setVPNRequestedProfile("")
        setVPNRequestedProfileFriendly("")
        setVPNLastConnectedProfile("")
        setVPNLastConnectedProfileFriendly("")
        setConnectionErrorCount(0)
        setConnectTime(addon)
        if isAlternative(vpn_provider):
            postConnectAlternative(vpn_provider)
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
        progress_message = "Cancelling connection attempt, restarting VPN monitor..."
        progress.update(97, progress_title, progress_message)
        # Set the final message to indicate cancellation
        progress_message = "Cancelling connection attempt, VPN monitor restarted"
        # Restore the previous connection info 
        dialog_message = "Cancelled connection attempt, VPN is disconnected\n"
        if not connection_order == "0":
            if not isVPNConnected():
                if cancel_clear:
                    dialog_message = dialog_message + "This connection has been removed from the list of valid connections"
                else:
                    dialog_message = dialog_message + "This connection has not been validated"
                resetVPNConfig(addon, int(connection_order))
        else:
            dialog_message = dialog_message + "Please reconnect"
            
        # If we selected the location, reset this so it can be selected next time
        if select_location: addon.setSetting("vpn_locations_list","")
        
        # Don't know how far we got, if we were trying to connect and then got cancelled,
        # there might still be an instance of openvpn running we need to kill
        stopVPN9()
        # We should also stop the service from trying to do a reconnect, if it's confused
        setVPNRequestedProfile("")
        setVPNRequestedProfileFriendly("")
        setVPNLastConnectedProfile("")
        setVPNLastConnectedProfileFriendly("")
        setVPNURL("")
        setConnectChange()
        setVPNState("off")
    else:
        # An error occurred, The current connection is already invalidated.  The VPN credentials might 
        # be ok, but if they need re-entering, the user must update them which will force a reset.
        if not reset_connections:
            progress_message = "Error connecting to VPN, restarting VPN monitor..."
        else:
            progress_message = "Restarting VPN monitor..."
        progress.update(97, progress_title, progress_message)
        xbmc.sleep(DIALOG_SPEED)
        # Set the final message to show an error occurred
        if not reset_connections:
            progress_message = "Error connecting to VPN, VPN monitor restarted"
        else:
            progress_message = "VPN monitor restarted"
        # First set of errors happened prior to trying to connect
        if not provider_download:
            if reset_connections:
                dialog_message = "Validate VPN connections to start using new locations"
            else:
                if not isAlternative(vpn_provider):
                    dialog_message = "Unable to download the VPN provider files. Check network and then try again. Additional information can be found in the log."
                else:
                    dialog_message = "Could not authenticate with VPN provider. Please check user name and password and try again."
            log_option = False
        elif not provider_gen:
            if isAlternative(vpn_provider):
                dialog_message = "Unable to retrieve location information from VPN provider. Check network and then try again. Additional information can be found in the log."
            else:
                dialog_message = "Error updating .ovpn files or creating user credentials file. Check log to determine cause of failure."
            log_option = False
        elif not got_keys:
            log_option = False
            if not keys_copied:
                if key_file == crt_file:
                    dialog_message = "Failed to extract user key or cert from ovpn file. Check opvn file and retry."
                else:
                    dialog_message = "Failed to copy supplied user key and cert files. Check log and retry."
            else:
                dialog_message = "User key and certificate files are required, but were not provided.  Locate the files or an ovpn file that contains them and try again."
        elif not got_key_pass:
            log_option = False
            dialog_message = "A password is needed for the user key, but was not entered. Try and connect again using the user key password."
        elif ovpn_name == "":
            log_option = False
            if isAlternative(vpn_provider):
                dialog_message = "Unable to retrieve VPN profile from VPN provider. Check network and then try again. Additional information can be found in the log."
            else:
                dialog_message = "No VPN profiles were available for " + vpn_protocol + ". They've all been used or none exist for the selected protocol filter."
        else:
            # This second set of errors happened because we tried to connect and failed
            if state == connection_status.AUTH_FAILED: 
                dialog_message = "Error connecting to VPN, authentication failed. Check your user name and password (or cert and key files).  If you've connected previously, check that your VPN plan allows access to this location, and supports multiple connections."
                credentials_path = getCredentialsPath(addon)
                if not connection_order == "0":
                    addon.setSetting("vpn_username_validated", "")
                    addon.setSetting("vpn_password_validated", "")
            elif state == connection_status.NETWORK_FAILED: 
                dialog_message = "Error connecting to VPN, could not establish connection. Check your user name, password and network connectivity and retry."
            elif state == connection_status.TIMEOUT:
                dialog_message = "Error connecting to VPN, connection has timed out or VPN could not be reached. Retry, or try using a different port or VPN profile."
            elif state == connection_status.ROUTE_FAILED:
                dialog_message = "Error connecting to VPN, could not update routing table. Retry and then check log."
            elif state == connection_status.ACCESS_DENIED:
                dialog_message = "Error connecting to VPN, could not update routing table. On Windows, Kodi must be run as administrator."
            elif state == connection_status.OPTIONS_ERROR:
                dialog_message = "Error connecting to VPN, unrecognised option. Disable block-outside-dns in debug menu, reset ovpn files and retry. Or check log and review ovpn file in use."
            elif state == connection_status.FILE_ERROR:
                dialog_message = "Error connecting to VPN, the .ovpn file required to make the connection could not be opened. Something has probably gone wrong earlier, check the Kodi log for additional information."
            else:
                dialog_message = "Error connecting to VPN, something unexpected happened. Check log for more information."
                addon.setSetting("ran_openvpn", "false")
            
            # Output what when wrong with the VPN to the log
            writeVPNLog()

        if not connection_order == "0" :
            resetVPNConfig(addon, int(connection_order))
        
        errorTrace("common.py", dialog_message)
        
        # If we selected the location, or reset the connections, clear the locations list for selecting next time
        if select_location or reset_connections: addon.setSetting("vpn_locations_list","")
        
        # The VPN might be having a spaz still so we want to ensure it's stopped
        stopVPN9()
        # We should also stop the service from trying to do a reconnect, if it's confused
        setVPNRequestedProfile("")
        setVPNRequestedProfileFriendly("")
        setVPNLastConnectedProfile("")
        setVPNLastConnectedProfileFriendly("")
        setVPNURL("")
        setConnectChange()
        setVPNState("off")

    # Restart service
    if not startService():
        progress.close()
        errorTrace("common.py", "VPN monitor service is not running, VPN has started")
        dialog_message = "Error, Service not running.\nCheck log and reboot."        
    else:
        # Close out the final progress dialog
        progress.update(100, progress_title, progress_message)
        xbmc.sleep(DIALOG_SPEED)
        progress.close()
    
    freeCycleLock()

    # Display connection result in an ok dialog
    if log_option:
        if xbmcgui.Dialog().yesno(progress_title, dialog_message, nolabel="OK", yeslabel="VPN Log"):
            popupOpenVPNLog(getVPNLocation(vpn_provider))
    else:
        xbmcgui.Dialog().ok(progress_title, dialog_message)
        
    if dns_error: 
        if getPlatform() == platforms.LINUX:
            xbmcgui.Dialog().ok(progress_title, "If you experience network or connectivity issues, consider running the [B]Potential DNS fix[/B] option in the [B]Advanced[/B] settings tab.")
        else:
            if not isCustom(): xbmcgui.Dialog().ok(addon_name, "If you experience network or connectivity issues, refer to the Kodi log and the [B]Trouble Shooting[/B] page found on the GitHub service.vpn.manager wiki.")
            else: xbmcgui.Dialog().ok(addon_name, "If you experience network or connectivity issues, refer to the Kodi log and your VPN provider support documentation.")            
    
    # Refresh the screen if this is not being done on settings screen
    if connection_order == "0" : xbmc.executebuiltin('Container.Refresh')
