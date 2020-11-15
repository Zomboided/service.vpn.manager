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
import time

DEC_ERR = "*** DECODE ERROR *** : "


def ifDebug():
    if getID() == "": return False
    if xbmcaddon.Addon(getID()).getSetting("vpn_enable_debug") == "true":
        return True
    return False

    
def ifHTTPTrace():
    if getID() == "": return False
    if xbmcaddon.Addon(getID()).getSetting("vpn_enable_http") == "true":
        return True
    return False


def ifJSONTrace():
    if xbmcgui.Window(10000).getProperty("VPN_Manager_JSON_Trace") == "true":
        return True
    return False
    
    
def alwaysLog():
    # FIXME PYTHON3 Stupid Leia/Matrix workaround because they needed to mess with the logging levels...
    # LOGNOTICE gets removed in Kodi 20 so this has a try/catch around this incase I forget to remove it
    try:
        if xbmcgui.Window(10000).getProperty("VPN_Manager_Kodi_Version").startswith("19"):
            return xbmc.LOGINFO
        else:
            return xbmc.LOGNOTICE
    except Exception as e:
        return xbmc.LOGINFO
    
    
def debugTrace(data):
    try:
        if ifDebug():
            log = getVery() + " : " + str(data)
            xbmc.log(msg=log, level=alwaysLog())       
        else:
            log = "VPN Mgr" + " : " + str(data)
            xbmc.log(msg=log, level=xbmc.LOGDEBUG)
    except Exception as e:
        log = DEC_ERR + getVery() + " : " + str(data)
        log = log.encode('ascii', 'ignore')
        xbmc.log(msg=log, level=xbmc.LOGERROR)
    
def errorTrace(module, data):
    log = getVery() + " : (" + module + ") " + str(data)
    try:
        xbmc.log(msg=log, level=xbmc.LOGERROR)
    except Exception as e:
        log = DEC_ERR + log
        log = log.encode('ascii', 'ignore')
        xbmc.log(msg=log, level=xbmc.LOGERROR)
    
def infoTrace(module, data):
    log = getVery() + " : (" + module + ") " + str(data)
    try:
        xbmc.log(msg=log, level=alwaysLog())
    except Exception as e:
        log = DEC_ERR + log
        log = log.encode('ascii', 'ignore')
        xbmc.log(msg=log, level=xbmc.LOGERROR)
    
def infoPrint(data):
    try:
        xbmc.log(msg=str(data), level=alwaysLog())
    except Exception as e:
        log = DEC_ERR + str(data)
        log = log.encode('ascii', 'ignore')
        xbmc.log(msg=log, level=xbmc.LOGERROR)

def newPrint(data):
    xbmc.log(msg=str(data), level=alwaysLog())

    
def now():
    return int(time.time())

    
def enum(**enums):
    return type('Enum', (), enums) 
    
    
def getID():
    return str(xbmcgui.Window(10000).getProperty("VPN_Addon_ID"))

def setID(id):
    xbmcgui.Window(10000).setProperty("VPN_Addon_ID", id)

    
def getName():
    return str(xbmcgui.Window(10000).getProperty("VPN_Addon_Name"))
    
def setName(name):
    xbmcgui.Window(10000).setProperty("VPN_Addon_Name", name)

    
def getShort():
    return str(xbmcgui.Window(10000).getProperty("VPN_Addon_Short_Name"))

def setShort(short_name):
    xbmcgui.Window(10000).setProperty("VPN_Addon_Short_Name", short_name)

    
def getVery():
    return str(xbmcgui.Window(10000).getProperty("VPN_Addon_Very_Short_Name"))
      
def setVery(very_short_name):
    xbmcgui.Window(10000).setProperty("VPN_Addon_Very_Short_Name", very_short_name)     
    
    
def running():
    if xbmcgui.Window(10000).getProperty("VPN_Service_Running") == "": return False
    return True
    
def setRunning(bool):
    if bool: xbmcgui.Window(10000).setProperty("VPN_Service_Running", "true")
    else: xbmcgui.Window(10000).setProperty("VPN_Service_Running", "")

    
    
def isCustom():
    if getID() == "": return False
    if not xbmcaddon.Addon(getID()).getSetting("vpn_custom") == "": return True
    return False

def getCustom():    
    return xbmcaddon.Addon(getID()).getSetting("vpn_custom")