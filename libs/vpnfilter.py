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
#    All the code to create an VPN Manager filter table and compare add-on
#    and window IDs against it.  Had no depedencies on other VPN Manager
#    modules so can be included in other add-ons to drive VPN switching


import xbmc
import xbmcaddon
import xbmcgui
import time

class FilterList:

    def __init__(self):
        # Class initialisation.  Fails with a RuntimeError exception if VPN Manager add-on is not available
        self.filtered_addons = []
        self.filtered_windows = []
        self.primary_vpns = []
        self.last_updated = 0
        self.timeout = 10
        if not xbmc.getCondVisibility("System.HasAddon(service.vpn.manager)"):
            xbmc.log("VPN Mgr : VPN Manager is not installed, cannot use filtering", level=xbmc.LOGERROR)
            raise RuntimeError("VPN Manager is not installed")

        
    def filterAndSwitch(self, path, windowid, wait):
        # Given a path to an addon, and/or a window ID, determine if it's associated with a particular VPN and
        # switch to that VPN.  Return True when the switch has happened or False if there's a problem switching 
        # (or there's no VPN that's been set up).  If the connected VPN is the VPN that's been identifed as being 
        # required, or no filter is found, just return True without messing with the connection.  The wait parameter
        # will determine if the function returns once the connection has been made, or if it's fire and forget.
        # If a stream is starting up after the VPN has been switched then wait should be set to True.
        if not self.isVPNSetUp():
            return False
        connection = self.isFiltered(path, windowid)
        if connection == 0:
            if self.getConnected() == "": return True
            xbmc.log(msg="VPN Mgr : Disconnecting due to filter " + path + " or window ID " + str(windowid), level=xbmc.LOGDEBUG)
            self.setAPICommand("Disconnect")
            if wait: return self.waitForConnection("")
        if connection > 0:
            if self.getConnected() == self.primary_vpns[connection]: return True
            xbmc.log(msg="VPN Mgr : Connecting to " + self.primary_vpns[connection] + " due to filter " + path + " or window ID " + str(windowid), level=xbmc.LOGDEBUG)
            self.setAPICommand(self.primary_vpns[connection])
            if wait: return self.waitForConnection(self.primary_vpns[connection])
        return True

            
    def setTimeOut(self, seconds):
        # Set filterAndSwitch timeout in seconds
        # Default is 30 seconds (recommended)
        # timeout is measured in half seconds
        self.timeout = seconds * 2

        
    def isFiltered(self, path, windowid):
        # Given the path to an addon, and/or a window ID, determine if it's associated with a particular VPN.
        # Return 0 if given addon is excluded (ie no VPN), 1 to 10 if it needs a particular VPN or -1 if not found
        # If we're already connected to a primary VPN and the add-on appears multiple times then return the 
        # current connected VPN if it matches, otherwise return the first.  If there are duplicate entries, 
        # disconnect will always win.

        # Get the timestamp from the home window as to when the vpn & filter lists were last changed
        try:
            changed = int(xbmcgui.Window(10000).getProperty("VPN_Manager_Lists_Last_Refreshed"))
        except:
            # If there's no refreshed time stamp, there are no filters to check against
            return -1
            
        if self.last_updated < changed:
            self.refreshLists()
        
        current = self.getCurrent()
        
        # Assume we're not gonna find anything
        found = -1

        # Try and filter on the path name.
        # Ignore local sources (that don't start with a ://)
        if ("://" in path):
            # Strip out the leading 'plugin://' or 'addons://' string, and anything trailing the plugin name
            filtered_addon_path = path[path.index("://")+3:]
            if "/" in filtered_addon_path:
                filtered_addon_path = filtered_addon_path[:filtered_addon_path.index("/")]
            # Can't filter if there's nothing to filter...
            if not filtered_addon_path == "":
                # Adjust 11 below if changing number of conn_max
                for i in range (0, 11):
                    if not self.filtered_addons[i] == None:
                        for filtered_string in self.filtered_addons[i]: 
                            if filtered_addon_path == filtered_string:
                                if found == -1 : found = i
                                if i > 0 and i == current : found = i
                # If we get a match return it
                if not found == -1: return found
                
        # Now try filtering on the window ID
        if windowid > 0:
            for i in range (0, 11):
                if not self.filtered_windows[i] == None:
                    for filtered_string in self.filtered_windows[i]:
                        if "-" in filtered_string:
                            low, high = filtered_string.split("-")
                            if windowid > int(low) and windowid < int(high):
                                if found == -1 : found = i
                                if i > 0 and i == current : found = i
                        else:
                            if str(windowid) == filtered_string:
                                if found == -1 : found = i
                                if i > 0 and i == current : found = i
        return found

        
    def isVPNSetUp(self):
        # Indicates if the VPN has been set up.  Can be called directly, but is used in filterAndSwitch
        # prior to messing withe the connection to ensure the VPN is running.
        addon = xbmcaddon.Addon("service.vpn.manager")
        if not addon.getSetting("1_vpn_validated") == "": return True
        return False


    def waitForConnection(self, connection_name):
        # Wait for the connection to change to the connection requested
        # Shouldn't need to call this directly
        for i in range(0, self.timeout):
            xbmc.sleep(500)
            if connection_name == self.getConnected():
                return True
        # Connection timed out
        return False

    
    def getConnected(self):
        return xbmcgui.Window(10000).getProperty("VPN_Manager_Connected_Profile_Name")
    
    
    def setAPICommand(self, profile):
        # Set up the API command for the main service to act upon
        # Shouldn't need to call this directly
        xbmcgui.Window(10000).setProperty("VPN_Manager_API_Command", profile)

        
    def getCurrent(self):
        # Compare the current connected VPN to the list of primary VPNs to see if one of the possible
        # filtered connections is in use.  Used by isFiltered, shouldn't be called directly
        found = 0
        current = xbmcgui.Window(10000).getProperty("VPN_Manager_Connected_Profile_Name")
        if current == "": return found
        # Adjust 10 below if changing number of conn_max
        for i in range (0, 10):                    
            if not self.primary_vpns[i] == "" and current == self.primary_vpns[i]:
                found = i+1
        return found
    
        
    def refreshLists(self):
        # This function will refresh the list of filters and VPNs being used.  It doesn't need to be called 
        # directly as it will be called before an add-on/window is checked if the data has changed
    
        # Get a handle to the VPN Mgr add-on to read the settings data
        addon = xbmcaddon.Addon("service.vpn.manager")
        
        del self.filtered_addons[:]
        del self.filtered_windows[:]
        del self.primary_vpns[:]
        
        # Adjust 11 below if changing number of conn_max
        for i in range (0, 11):
        
            # Load up the list of primary VPNs
            if i>0: self.primary_vpns.append(addon.getSetting(str(i)+"_vpn_validated"))
        
            # Load up the addon filter list
            addon_string = ""
            if i == 0 : addon_string = addon.getSetting("vpn_excluded_addons")
            else : addon_string = addon.getSetting(str(i)+"_vpn_addons")
            if not addon_string == "" : self.filtered_addons.append(addon_string.split(","))
            else : self.filtered_addons.append(None)   

            # Load up the window filter list
            window_string = ""
            if i == 0 : window_string = addon.getSetting("vpn_excluded_windows")
            else : window_string = addon.getSetting(str(i)+"_vpn_windows")
            if not window_string == "" : self.filtered_windows.append(window_string.split(","))
            else : self.filtered_windows.append(None)

        # Store the time the filters were last updated
        self.last_updated = int(time.time())
        