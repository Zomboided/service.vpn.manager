#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#    Copyright (C) 2018 Zomboided
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
#    Setters and getters

import xbmc
import xbmcaddon
import xbmcgui
from libs.utility import ifHTTPTrace, ifJSONTrace, debugTrace, infoTrace, errorTrace, ifDebug, newPrint, getID, now


# These are duplicated here to avoid a circular reference in common.
# Probably should break all the getters and setters out into a separate lib sometime
def setVPNRequestedServer(server_name):
    # Store server name
    xbmcgui.Window(10000).setProperty("VPN_Manager_Requested_Server_Name", server_name)
    return

def getVPNRequestedServer():
    # Return server name
    return xbmcgui.Window(10000).getProperty("VPN_Manager_Requested_Server_Name") 

    
# Manage the authentication tokens
def resetTokens():
    setTokens("", "", "")
    
def setTokens(token, renew, creds):
    xbmcgui.Window(10000).setProperty("VPN_Manager_Alternative_Token", token)
    xbmcgui.Window(10000).setProperty("VPN_Manager_Alternative_Renew", renew)
    # Renew time is a day after token creation
    if not renew == "": 
        xbmcgui.Window(10000).setProperty("VPN_Manager_Alternative_Expiry", str(now() + 86400))
    else:
        xbmcgui.Window(10000).setProperty("VPN_Manager_Alternative_Expiry", "")
    if not creds == None : xbmcgui.Window(10000).setProperty("VPN_Manager_Alternative_Credentials", creds)
    
def getTokens():
    return xbmcgui.Window(10000).getProperty("VPN_Manager_Alternative_Token"), xbmcgui.Window(10000).getProperty("VPN_Manager_Alternative_Renew"), xbmcgui.Window(10000).getProperty("VPN_Manager_Alternative_Expiry"), xbmcgui.Window(10000).getProperty("VPN_Manager_Alternative_Credentials")
