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
#    Code fragments specific to NordVPN.

import xbmc
import xbmcaddon
import xbmcgui
import json
from utility import debugTrace, infoTrace, errorTrace, ifDebug, newPrint


# These are duplicated here to avoid a circular reference in common.
# Probably should break all the getters and setters out into a separate lib sometime
def setVPNRequestedServer(server_name):
    # Store server name
    xbmcgui.Window(10000).setProperty("VPN_Manager_Requested_Server_Name", server_name)
    return

def getVPNRequestedServer():
    # Return server name
    return xbmcgui.Window(10000).getProperty("VPN_Manager_Requested_Server_Name") 


def getNordVPNPreFetch(vpn_provider):
    # Optionally prefetch info from the magical internet to make the connection process smoother
    # FIXME
    return True

    
def getNordVPNLocations(vpn_provider, exclude_used):
    # Return a list of all of the locations
    # FIXME Need to filter on the protocol and remove the connections already selected
    return ["c:\\England.ovpn\\", "c:\\user\\Scotland.ovpn", "c:\\user\\Wales.ovpn", "c:\\user\\Ireland.ovpn"]    
    

def getNordVPNFriendlyLocations(vpn_provider, exclude_used):
    # Return a list of all of the locations
    # FIXME Need to remove the location that's already been connected and filter on the protocol
    return ["England", "Scotland", "Wales", "Ireland"]


def getNordVPNLocationName(vpn_provider, location):
    return getAddonPath(True, vpn_provider + "/" + location + ".ovpn")

    
def getNordVPNLocation(vpn_provider, location, server_count):
        return "", ""

        
def getNordVPNOvpnFile(server, protocol, target_file):
        return False

    
def getNordVPNServers(vpn_provider, exclude_used):
    # Return a list of all of the servers
    # FIXME Need to remove the location that's already been connected and filter on the protocol
    return ["1.2.3.4", "2.3.4.5"]
       
    
def getNordVPNFriendlyServers(vpn_provider, exclude_used):
    # Return a list of all of the servers
    # FIXME Need to remove the location that's already been connected and filter on the protocol
    return ["c:\\user\\1.2.3.4.ovpn", "c:\\user\\2.3.4.5.ovpn"] 
    

def getNordVPNLocation(vpn_provider, location, server_count):
    # Return friendly name and .ovpn file name
    # FIXME 
    return location, "c:\\user\\" + location + ".ovpn"
    
    
def getNordVPNServer(vpn_provider, server, server_count):
    # Return friendly name and .ovpn file name
    # FIXME
    return server, "c:\\user\\" + server + ".ovpn"
    

def regenerateNordVPN(vpn_provider)
    # Regenerate the files for the validated connections
    # FIXME
    return True