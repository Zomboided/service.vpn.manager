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
#    Code fragments specific to individual VPN providers.

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
import json
import urllib2
import time
from libs.utility import ifHTTPTrace, ifJSONTrace, debugTrace, infoTrace, errorTrace, ifDebug, newPrint, getID, now
from libs.platform import getAddonPath
from libs.access import setVPNRequestedServer, getVPNRequestedServer, resetTokens, setTokens, getTokens



def getShellfirePreFetch(vpn_provider):
    # <FIXME>
    return True
    
    
def getShellfireFriendlyLocations(vpn_provider, exclude_used):
    # <FIXME>
    return []


def getShellfireLocations(vpn_provider, exclude_used):
    # <FIXME>
    return []


def getShellfireLocationName(vpn_provider, location):
    # <FIXME> although this is probably right
    return getAddonPath(True, vpn_provider + "/" + location + ".ovpn")
    
    
def getShellfireLocation(vpn_provider, location, server_count):
    # <FIXME>
    return "", ""
    

def getShellfireServers(vpn_provider, exclude_used):
    # Return a list of all of the server files
    # Not supported for this provider
    return []

    
def getShellfireFriendlyServers(vpn_provider, exclude_used):
    # Return a list of all of the servers
    # Not supported for this provider
    return []


def getShellfireServer(vpn_provider, server, server_count):
    # Return friendly name and .ovpn file name
    # Not supported for this provider
    return "", ""
    

def regenerateShellfire(vpn_provider):
    # <FIXME>
    return True


def resetShellfire(vpn_provider):
    # <FIXME>
    return True
    
    
def authenticateShellfire(vpn_provider, username, password):
    # <FIXME>
    return True


def getShellfireUserPass(vpn_provider):
    # <FIXME>
    return "", ""
    


