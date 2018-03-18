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

import xbmc
import xbmcaddon
import xbmcgui


def ifDebug():
    if getID() == "": return False
    if xbmcaddon.Addon(getID()).getSetting("vpn_enable_debug") == "true":
        return True
    return False

    
def debugTrace(data):    
    if ifDebug():
        log = getVery() + " : " + data
        xbmc.log(msg=log, level=xbmc.LOGNONE)       
    else:
        log = getVery() + " : " + data
        xbmc.log(msg=log, level=xbmc.LOGDEBUG)
    
    
def errorTrace(module, data):
    log = getVery() + " : (" + module + ") " + data
    xbmc.log(msg=log, level=xbmc.LOGERROR)
    
    
def infoTrace(module, data):
    log = getVery() + " : (" + module + ") " + data
    xbmc.log(msg=log, level=xbmc.LOGNOTICE)

    
def infoPrint(data):
    xbmc.log(msg=data, level=xbmc.LOGNOTICE)


def newPrint(data):
    xbmc.log(msg=data, level=xbmc.LOGERROR)

    
def enum(**enums):
    return type('Enum', (), enums) 
    
    
def getID():
    return xbmcgui.Window(10000).getProperty("VPN_Addon_ID")

def setID(id):
    return xbmcgui.Window(10000).setProperty("VPN_Addon_ID", id)

    
def getName():
    return xbmcgui.Window(10000).getProperty("VPN_Addon_Name")
    
def setName(name):
    return xbmcgui.Window(10000).setProperty("VPN_Addon_Name", name)

    
def getShort():
    return xbmcgui.Window(10000).getProperty("VPN_Addon_Short_Name")

def setShort(short_name):
    return xbmcgui.Window(10000).setProperty("VPN_Addon_Short_Name", short_name)

    
def getVery():
    return xbmcgui.Window(10000).getProperty("VPN_Addon_Very_Short_Name")
      
def setVery(very_short_name):
    return xbmcgui.Window(10000).setProperty("VPN_Addon_Very_Short_Name", very_short_name)     
    