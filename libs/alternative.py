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

    
def authenticateNordVPN(userid, password):
    return False
    
    
def getNordVPNPreFetch(vpn_provider):
    return True

    
def getNordVPNLocations(vpn_provider, exclude_used):
    return [""]    
    

def getNordVPNFriendlyLocations(vpn_provider, exclude_used):
    return [""]


def getNordVPNLocationName(vpn_provider, location):
    return ""

    
def getNordVPNLocation(vpn_provider, location, server_count):
    return "", ""

        
def getNordVPNOvpnFile(server, protocol, target_file):
    return False

    
def getNordVPNServers(vpn_provider, exclude_used):
    return []
       
    
def getNordVPNFriendlyServers(vpn_provider, exclude_used):
    return []

    
def getNordVPNServer(vpn_provider, server, server_count):
    return "", ""
    
    
def regenerateNordVPN(vpn_provider):
    return True
    
    
def resetNordVPN(vpn_provider):
    return True  