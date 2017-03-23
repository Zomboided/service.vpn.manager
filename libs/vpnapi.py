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
#    All the code to access the API for the filtering and switching 
#    functionality of VPN Manager.  Can be imported from the service.vpn.manager 
#    add-on or can be copied as a complete file and included in a third party 
#    add-on directly


import xbmc
import xbmcaddon
import xbmcgui
import time

class VPNAPI:

    def __init__(self):
        # Class initialisation.  Fails with a RuntimeError exception if VPN Manager add-on is not available, or too old
        self.filtered_addons = []
        self.filtered_windows = []
        self.primary_vpns = []
        self.last_updated = 0
        self.refreshLists()
        self.default = self.getConnected()
        xbmc.log("VPN Mgr API : Default is " + self.default, level=xbmc.LOGDEBUG)
        self.timeout = 30
        if not xbmc.getCondVisibility("System.HasAddon(service.vpn.manager)"):
            xbmc.log("VPN Mgr API : VPN Manager is not installed, cannot use filtering", level=xbmc.LOGERROR)
            raise RuntimeError("VPN Manager is not installed")
        else:
            v = int((xbmcaddon.Addon("service.vpn.manager").getAddonInfo("version").strip()).replace(".",""))
            if v < 310:
                raise RuntimeError("VPN Manager " + str(v) + " installed, but needs to be v3.1.0 or later")

                
    def isVPNSetUp(self):
        # Indicates if the VPN has been set up.  Can be called directly, but is used by
        # all calls that mess with the connection to ensure the VPN is running.
        addon = xbmcaddon.Addon("service.vpn.manager")
        if not addon.getSetting("1_vpn_validated") == "": return True
        return False
        
    
    def connectToValidated(self, connection, wait):
        # Given the number of a validated connection, connect to it.  Return True when the connection has happened 
        # or False if there's a problem connecting (or there's not a VPN connection available for this connection 
        # number).  Return True without messing with the connection if the current VPN is the same as the VPN being
        # requested.  The wait parameter will determine if the function returns once the connection has been made, 
        # or if it's fire and forget (in which case True will be returned regardless)
        if not self.isVPNSetUp(): return False
        if connection < 1 or connection > 10: return False
        connection = connection - 1
        self.refreshLists()
        if self.primary_vpns[connection] == "": return False
        if self.getConnected() == self.primary_vpns[connection]: return True
        xbmc.log(msg="VPN Mgr API : Connecting to " + self.primary_vpns[connection], level=xbmc.LOGDEBUG)
        self.setAPICommand(self.primary_vpns[connection])
        if wait: return self.waitForConnection(self.primary_vpns[connection])
        return True
                

    def connectTo(self, connection_name, wait):
        # Given the ovpn filename of a connection, connect to it.  Return True when the connection has happened 
        # or False if there's a problem connecting (or there's not a VPN connection available for this connection 
        # number).  Return True without messing with the connection if the current VPN is the same as the VPN being
        # requested.  The wait parameter will determine if the function returns once the connection has been made, 
        # or if it's fire and forget (in which case True will be returned regardless)
        if not self.isVPNSetUp(): return False
        if connection_name == "": return False
        if self.getConnected() == connection_name: return True
        xbmc.log(msg="VPN Mgr API : Connecting to " + connection_name, level=xbmc.LOGDEBUG)
        self.setAPICommand(connection_name)
        if wait: return self.waitForConnection(connection_name)
        return True

                
    def disconnect(self, wait):
        # Disconnect any active VPN connection.  Return True when the connection has disconnected.  If there's
        # not an active connection, return True anyway.  The wait parameter will determine if the function returns 
        # once the connection has been made, or if it's fire and forget (in which case True will be returned regardless)
        if not self.isVPNSetUp(): return False
        if self.getConnected() == "": return True
        xbmc.log(msg="VPN Mgr API : Disconnecting", level=xbmc.LOGDEBUG)
        self.setAPICommand("Disconnect")
        if wait: return self.waitForConnection("")
        return True

        
    def defaultVPN(self, wait):
        # Return to the default VPN state.  This is a wrapper function to disconnect() and connectTo() with
        # the behaviour and return values matching those functions.
        if self.default == "":
            return self.disconnect(wait)
        else:
            return self.connectTo(self.default, wait)
        
        
    def filterAndSwitch(self, path, windowid, default, wait):
        # Given a path to an addon, and/or a window ID, determine if it's associated with a particular VPN and
        # switch to that VPN.  Return True when the switch has happened or False if there's a problem switching 
        # (or there's no VPN that's been set up).  If the connected VPN is the VPN that's been identifed as being 
        # required, or no filter is found, just return True without messing with the connection.  The default 
        # parameter is a boolean indicating if the default VPN should be connected to if no filter is found.
        # The wait parameter will determine if the function returns once the connection has been made, or if it's 
        # fire and forget (in which case True will be returned regardless).  
        if not self.isVPNSetUp():
            return False
        connection = self.isFiltered(path, windowid)
        # Switch to the default connection if there's no filter
        if connection == -1 and default : 
            xbmc.log(msg="VPN Mgr API : Reconnecting to the default", level=xbmc.LOGDEBUG)
            return self.defaultVPN(wait)
        if connection == 0:
            if self.getConnected() == "": return True
            xbmc.log(msg="VPN Mgr API : Disconnecting due to filter " + path + " or window ID " + str(windowid), level=xbmc.LOGDEBUG)
            self.setAPICommand("Disconnect")
            if wait: return self.waitForConnection("")
        if connection > 0:
            connection = connection - 1
            if self.primary_vpns[connection] == "": return False
            if self.getConnected() == self.primary_vpns[connection]: return True
            xbmc.log(msg="VPN Mgr API : Connecting to " + self.primary_vpns[connection] + " due to filter " + path + " or window ID " + str(windowid), level=xbmc.LOGDEBUG)
            self.setAPICommand(self.primary_vpns[connection])
            if wait: return self.waitForConnection(self.primary_vpns[connection])
        return True
      
            
    def isFiltered(self, path, windowid):
        # Given the path to an addon, and/or a window ID, determine if it's associated with a particular VPN.
        # Return 0 if given addon is excluded (ie no VPN), 1 to 10 if it needs a particular VPN or -1 if not found
        # If we're already connected to a primary VPN and the add-on appears multiple times then return the 
        # current connected VPN if it matches, otherwise return the first.  If there are duplicate entries, 
        # disconnect will always win.
        # Get the latest filter data and the current connection
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

        
    def setTimeOut(self, seconds):
        # Set filterAndSwitch timeout in seconds
        # Default is 30 seconds (recommended)
        # timeout is measured in half seconds
        self.timeout = seconds * 2        
        
        
    def setDefault(self, default):
        # Override the default connection.  Expects to be passed the name of the connection as an 
        # ovpn file name.  This is probably only needed when the API object is old and crusty and
        # there's potential that the .ovpn has changed.  Might be better just to create a new
        # API object in this case though...
        self.default = default
        
        
    # Functions below this line shouldn't need to be called directly

        
        
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
        found = -1
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
        try:
            changed = int(xbmcgui.Window(10000).getProperty("VPN_Manager_Lists_Last_Refreshed"))
        except:
            # If there's no refreshed time stamp, force a refresh with whatever data is available
            changed = self.last_updated
        if self.last_updated > changed:
            return
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
