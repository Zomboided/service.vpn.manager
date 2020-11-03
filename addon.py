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
#    This module displays the menu options

import xbmc
import xbmcaddon
import xbmcplugin
import xbmcgui
import os
from libs.common import connectionValidated, getIPInfo, isVPNConnected, getVPNProfileFriendly
from libs.common import getFriendlyProfileList, connectVPN, disconnectVPN, setVPNState, requestVPNCycle, getFilteredProfileList
from libs.common import isVPNMonitorRunning, setVPNMonitorState, getVPNMonitorState, wizard
from libs.common import getIconPath, getSystemData, getVPNServer
from libs.vpnplatform import getPlatform, platforms, getPlatformString, fakeConnection
from libs.vpnproviders import getAddonList, isAlternative, getAlternativeLocations, getAlternativeFriendlyLocations, getAlternativeLocation
from libs.vpnproviders import allowReconnection
from libs.utility import debugTrace, errorTrace, infoTrace, newPrint, getID, getName
from libs.access import getVPNURL, getVPNProfile
from libs.sysbox import popupSysBox


debugTrace("-- Entered addon.py " + sys.argv[0] + " " + sys.argv[1] + " " + sys.argv[2] + " --")

# Set the addon name for use in the dialogs
addon = xbmcaddon.Addon()
addon_name = addon.getAddonInfo("name")
addon_id = addon.getAddonInfo('id')

# Get the arguments passed in
base_url = sys.argv[0]
addon_handle = int(sys.argv[1])
args = sys.argv[2].split("?", )
action = ""
params = ""
# If an argument has been passed in, the first character will be a ?, so the first list element is empty
inc = 0
for token in args:
    if inc == 1 : action = token
    if inc > 1 : params = params + token
    inc = inc + 1  

# Don't seem to need to do this on *nix platforms as the filename will be different
if getPlatform() == platforms.WINDOWS: params = params.replace("/", "\\")

debugTrace("Parsed arguments to action=" + action + " params=" + params)

    
def topLevel():
    # Build the top level menu with URL callbacks to this plugin
    debugTrace("Displaying the top level menu")
    url = base_url + "?settings"
    li = xbmcgui.ListItem("Settings")
    li.setArt({"icon":getIconPath()+"settings.png"})
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li)
    url = base_url + "?display"
    li = xbmcgui.ListItem("Display VPN status")
    li.setArt({"icon":getIconPath()+"display.png"})
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li)
    if addon.getSetting("vpn_system_menu_item") == "true":
        url = base_url + "?system"
        li = xbmcgui.ListItem("Display enhanced information")
        li.setArt({"icon":getIconPath()+"enhanced.png"})
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=True)
    url = base_url + "?list"
    li = xbmcgui.ListItem("Change or disconnect VPN connection")
    li.setArt({"icon":getIconPath()+"locked.png"})
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=True)
    url = base_url + "?cycle"
    li = xbmcgui.ListItem("Cycle through primary VPN connections")
    li.setArt({"icon":getIconPath()+"cycle.png"})
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li)
    url = base_url + "?switch"
    if not getVPNMonitorState() == "":
        if isVPNMonitorRunning():
            li = xbmcgui.ListItem("Pause add-on filtering")
            li.setArt({"icon":getIconPath()+"paused.png"})
        else:
            li = xbmcgui.ListItem("Restart add-on filtering")
            li.setArt({"icon":getIconPath()+"play.png"})
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li)
    xbmcplugin.endOfDirectory(addon_handle)
    return


def listSystem(addon):
    lines = getSystemData(addon, True, True, True, True)
    for line in lines:
        url = base_url + "?back"
        li = xbmcgui.ListItem(line)
        li.setArt({"icon":getIconPath()+"enhanced.png"})
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li)
    xbmcplugin.endOfDirectory(addon_handle)
    return


def displaySystem():
    popupSysBox()
    return
    
    
def back():
    xbmc.executebuiltin("Action(ParentDir)")
    return
    

def displayStatus():
    # Create a busy dialog whilst the data is retrieved.  It
    # could take a while to deduce that the network is bad...
    xbmc.executebuiltin('ActivateWindow(busydialognocancel)')
    try:
        _, ip, country, isp = getIPInfo(addon)
        if isVPNConnected():
            debugTrace("VPN is connected, displaying the connection info")
            xbmc.executebuiltin('Dialog.Close(busydialognocancel)')
            # Display the server if enhanced system info is switched on
            server = ""
            if addon.getSetting("vpn_server_info") == "true":
                server = getVPNURL()
            if not server == "": server = "\nServer is " + server + "\n"
            else: server = "\n"
            ovpn_name = getVPNProfileFriendly()
            if fakeConnection():
                xbmcgui.Dialog().ok(addon_name, "[B]Faked connection to a VPN[/B]\nProfile is " + ovpn_name + server + "Using " + ip + ", located in " + country + "\nService Provider is " + isp)
            else:
                xbmcgui.Dialog().ok(addon_name, "[B]Connected to a VPN[/B]\nProfile is " + ovpn_name + server + "Using " + ip + ", located in " + country + "\nService Provider is " + isp)
        else:
            debugTrace("VPN is not connected, displaying the connection info")
            xbmc.executebuiltin('Dialog.Close(busydialognocancel)')
            xbmcgui.Dialog().ok(addon_name, "[B]Disconnected from VPN[/B]\nUsing " + ip + ", located in " + country +"+\nService Provider is " + isp)
    except Exception:
        xbmc.executebuiltin('Dialog.Close(busydialognocancel)')
    return

    
def listConnections():
    # Start with the disconnect option
    url = base_url + "?disconnect"
    if getVPNProfileFriendly() == "":
        li = xbmcgui.ListItem("[COLOR ffff0000](Disconnected)[/COLOR]")
        li.setArt({"icon":getIconPath()+"disconnected.png"})
    else:
        li = xbmcgui.ListItem("[COLOR ffff0000]Disconnect[/COLOR]")
        li.setArt({"icon":getIconPath()+"unlocked.png"})
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li)

    # We should have a VPN set up by now, but don't list if we haven't.
    vpn_provider = addon.getSetting("vpn_provider")
    debugTrace("Listing the connections available for " + vpn_provider)
    if not vpn_provider == "":
        # Get the list of connections and add them to the directory
        if not isAlternative(vpn_provider):
            all_connections = getAddonList(vpn_provider, "*.ovpn")
            ovpn_connections = getFilteredProfileList(all_connections, addon.getSetting("vpn_protocol"), None)
            connections = getFriendlyProfileList(ovpn_connections, "", "")
        else:
            ovpn_connections = getAlternativeLocations(vpn_provider, False)
            connections = getAlternativeFriendlyLocations(vpn_provider, False)
        inc = 0
        for connection in ovpn_connections:
            if not isAlternative(vpn_provider):
                # Regular connections have the ovpn filename added ot the URL
                url = base_url + "?change?" + ovpn_connections[inc]
            else:
                # Alternative connections use the friendly name which can then be resolved later
                url = base_url + "?change?" + connections[inc]
            conn_text = ""
            conn_primary = ""
            i=1
            # Adjust 10 and 11 below if changing number of conn_max
            while (i < 11):
                if addon.getSetting(str(i) + "_vpn_validated_friendly") == connections[inc].strip(" ") :
                    conn_primary = " (" + str(i) + ")"
                    i = 10
                i=i+1

            if getVPNProfileFriendly() == connections[inc].strip(" ") and isVPNConnected(): 
                conn_text = "[COLOR ff00ff00]" + connections[inc] + conn_primary + " (Connected)[/COLOR]"
                if fakeConnection():
                    icon = getIconPath()+"faked.png"
                else:
                    icon = getIconPath()+"connected.png"
            else:
                if not conn_primary == "":
                    conn_text = "[COLOR ff0099ff]" + connections[inc] + conn_primary + "[/COLOR]"
                else:
                    conn_text = connections[inc] + conn_primary
                icon = getIconPath()+"locked.png"                
            li = xbmcgui.ListItem(conn_text)
            li.setArt({"icon":icon})
            xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li)
            inc = inc + 1
    xbmcplugin.endOfDirectory(addon_handle)            
    return

    
def disconnect():
    # Disconnect or display status if already disconnected
    debugTrace("Disconnect selected from connections menu")
    if isVPNConnected():
        disconnectVPN(True)
        setVPNState("off")
    else:
        displayStatus()
    return
    
    
def changeConnection():
    # Connect, or display status if we're already using selected VPN profile
    # If there is no profile, then skip this as the user has selected something non-selectable
    debugTrace("Changing connection to " + params + " from " + getVPNProfile() + ", connected:" + str(isVPNConnected()))
    addon = xbmcaddon.Addon(getID())
    ignore = False
    user_text = ""
    vpn_provider = addon.getSetting("vpn_provider")
    if isAlternative(vpn_provider):
        # Convert the friendly name to a file name, or an error message
        _, ovpn_connection, user_text, ignore = getAlternativeLocation(vpn_provider, params, 0, True)
    else:
        # Just extract the ovpn name from the URL for regular providers
        ovpn_connection = params
    # Try and connect if we've got a connection name.  If we're already connection, display the status
    if not ignore:
        if not user_text == "":
            xbmcgui.Dialog().ok(addon_name, user_text)
        elif isVPNConnected() and ovpn_connection == getVPNProfile() and not allowReconnection(vpn_provider) and not addon.getSetting("allow_cycle_reconnect") == "true":
            displayStatus()
        else:        
            connectVPN("0", ovpn_connection)
    return


def cycleConnection():
    # Cycle through the connections
    debugTrace("Cycling through available connections")
    requestVPNCycle(False)
    return
    

def switchService():
    debugTrace("Switching monitor state, current state is " + getVPNMonitorState())
    if isVPNMonitorRunning():
        setVPNMonitorState("Stopped")
        addon.setSetting("monitor_paused", "true")
        infoTrace("addon.py", "VPN monitor service paused")
    else:
        setVPNMonitorState("Started")
        addon.setSetting("monitor_paused", "false")
        infoTrace("addon.py", "VPN monitor service restarted")
    xbmc.executebuiltin('Container.Refresh')
    return


if action == "display": 
    # Display the network status
    displayStatus()
elif action == "system":
    displaySystem()
elif action == "back" : 
    back()
elif not connectionValidated(addon) and action != "":
    # Haven't got a valid connection so force user into the wizard or the settings dialog
    if addon.getSetting("vpn_wizard_enabled") == "true":
        wizard()
    else:
        if not action == "settings":
            xbmcgui.Dialog().ok(addon_name, "A VPN hasn't been set up yet.  Click Ok to open the settings.")
        command = "Addon.OpenSettings(" + addon_id + ")"
        xbmc.executebuiltin(command)   
else:
    # User wants to see settings, list connections or they've selected to change something.  
    # If it's none of these things, we're at the top level and just need to show the menu
    if action == "settings" :
        debugTrace("Opening settings")
        command = "Addon.OpenSettings(" + addon_id + ")"
        xbmc.executebuiltin(command)    
    elif action == "list" : listConnections()
    elif action == "disconnect" : disconnect()
    elif action == "change" : changeConnection()
    elif action == "cycle" : cycleConnection()
    elif action == "switch" : switchService()

    else: topLevel()

debugTrace("-- Exit addon.py --")    