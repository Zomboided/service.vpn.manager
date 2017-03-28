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
#    This module displays the VPN Manager for OpenVPN menu options

import xbmc
import xbmcaddon
import xbmcplugin
import xbmcgui
import os
from libs.common import connectionValidated, getIPInfo, isVPNConnected, getVPNProfile, getVPNProfileFriendly
from libs.common import getFriendlyProfileList, connectVPN, disconnectVPN, setVPNState, requestVPNCycle, getFilteredProfileList
from libs.common import isVPNMonitorRunning, setVPNMonitorState, getVPNMonitorState, wizard
from libs.common import getIconPath, getSystemData
from libs.platform import getPlatform, platforms, getPlatformString, fakeConnection
from libs.vpnproviders import getAddonList
from libs.utility import debugTrace, errorTrace, infoTrace


debugTrace("-- Entered addon.py " + sys.argv[0] + " " + sys.argv[1] + " " + sys.argv[2] + " --")

# Set the addon name for use in the dialogs
addon = xbmcaddon.Addon()
addon_name = addon.getAddonInfo("name")

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
    li = xbmcgui.ListItem("Add-on Settings", iconImage=getIconPath()+"settings.png")
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li)
    url = base_url + "?display"
    li = xbmcgui.ListItem("Display VPN status", iconImage=getIconPath()+"display.png")
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li)
    if addon.getSetting("vpn_system_menu_item") == "true":
        url = base_url + "?system"
        li = xbmcgui.ListItem("Display enhanced information", iconImage=getIconPath()+"enhanced.png")
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=True)
    url = base_url + "?list"
    li = xbmcgui.ListItem("Change or disconnect VPN connection", iconImage=getIconPath()+"locked.png")
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=True)
    url = base_url + "?cycle"
    li = xbmcgui.ListItem("Cycle through primary VPN connections", iconImage=getIconPath()+"cycle.png")
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li)
    url = base_url + "?switch"
    if isVPNMonitorRunning():
        li = xbmcgui.ListItem("Pause add-on filtering", iconImage=getIconPath()+"paused.png")
    else:
        li = xbmcgui.ListItem("Restart add-on filtering", iconImage=getIconPath()+"play.png")
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li)
    xbmcplugin.endOfDirectory(addon_handle)
    return


def listSystem(addon):
    lines = getSystemData(addon, True, True, True, True)
    for line in lines:
        url = base_url + "?back"
        li = xbmcgui.ListItem(line, iconImage=getIconPath()+"enhanced.png")
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li)
    xbmcplugin.endOfDirectory(addon_handle)
    return


def back():
    xbmc.executebuiltin("Action(ParentDir)")
    return
    

def displayStatus():
    _, ip, country, isp = getIPInfo(addon)
    if isVPNConnected():
        debugTrace("VPN is connected, displaying the connection info")
        if fakeConnection():
            xbmcgui.Dialog().ok(addon_name, "Faked connection to a VPN in " + country + ".\nUsing profile " + getVPNProfileFriendly() + ".\nExternal IP address is " + ip + ".\nService Provider is " + isp)
        else:
            xbmcgui.Dialog().ok(addon_name, "Connected to a VPN in " + country + ".\nUsing profile " + getVPNProfileFriendly() + ".\nExternal IP address is " + ip + ".\nService Provider is " + isp)
    else:
        debugTrace("VPN is not connected, displaying the connection info")
        xbmcgui.Dialog().ok(addon_name, "Disconnected from VPN.\nNetwork location is " + country + ".\nIP address is " + ip + ".\nService Provider is " + isp)
    return

    
def listConnections():
    # Start with the disconnect option
    url = base_url + "?disconnect"
    if getVPNProfileFriendly() == "":
        li = xbmcgui.ListItem("[COLOR ffff0000](Disconnected)[/COLOR]", iconImage=getIconPath()+"disconnected.png")
    else:
        li = xbmcgui.ListItem("[COLOR ffff0000]Disconnect[/COLOR]", iconImage=getIconPath()+"unlocked.png")
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li)

    # We should have a VPN set up by now, but don't list if we haven't.
    vpn_provider = addon.getSetting("vpn_provider")
    debugTrace("Listing the connections available for " + vpn_provider)
    if vpn_provider != "":
        # Get the list of connections and add them to the directory
        all_connections = getAddonList(vpn_provider, "*.ovpn")
        ovpn_connections = getFilteredProfileList(all_connections, addon.getSetting("vpn_protocol"), None)
        connections = getFriendlyProfileList(ovpn_connections)
        inc = 0
        for connection in ovpn_connections:
            url = base_url + "?change?" + ovpn_connections[inc]
            conn_text = ""
            conn_primary = ""
            i=1
            # Adjust 10 and 11 below if changing number of conn_max
            while (i < 11):
                if addon.getSetting(str(i) + "_vpn_validated_friendly") == connections[inc] :
                    conn_primary = " (" + str(i) + ")"
                    i = 10
                i=i+1

            if getVPNProfileFriendly() == connections[inc] and isVPNConnected(): 
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
            li = xbmcgui.ListItem(conn_text, iconImage=icon)
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
    debugTrace("Changing connection to " + params + " from " + getVPNProfile() + ", connected:" + str(isVPNConnected()))
    if isVPNConnected() and params == getVPNProfile():
        displayStatus()
    else:        
        connectVPN("0", params)
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
    listSystem(addon)
elif action == "back" : 
    back()
    #listSystem()
elif not connectionValidated(addon) and action != "":
    # Haven't got a valid connection so force user into the wizard or the settings dialog
    if not addon.getSetting("vpn_wizard_run") == "true" : 
        wizard()
    else:
        if not action =="settings": xbmcgui.Dialog().ok(addon_name, "Please validate a primary VPN connection first.  You can do this using the VPN Configuration and VPN Connections tabs within the Settings dialog.")
    xbmc.executebuiltin("Addon.OpenSettings(service.vpn.manager)")
else:
    # User wants to see settings, list connections or they've selected to change something.  
    # If it's none of these things, we're at the top level and just need to show the menu
    if action == "settings" :
        debugTrace("Opening settings")
        xbmc.executebuiltin("Addon.OpenSettings(service.vpn.manager)")    
    elif action == "list" : listConnections()
    elif action == "disconnect" : disconnect()
    elif action == "change" : changeConnection()
    elif action == "cycle" : cycleConnection()
    elif action == "switch" : switchService()

    else: topLevel()

debugTrace("-- Exit addon.py --")    