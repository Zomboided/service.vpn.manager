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
#    Shared code fragments used by the VPN Manager for OpenVPN add-on.

import xbmc
import xbmcaddon

addon = xbmcaddon.Addon("service.vpn.manager")
addon_name = addon.getAddonInfo("name")


def ifDebug():
    if addon.getSetting("vpn_enable_debug") == "true":
        return True
    return False

    
def debugTrace(data):    
    log = "VPN Mgr : " + data
    if addon.getSetting("vpn_enable_debug") == "true":
        print log        
    else:
        xbmc.log(msg=log, level=xbmc.LOGDEBUG)
    
    
def errorTrace(module, data):
    log = "VPN Mgr : (" + module + ") " + data
    xbmc.log(msg=log, level=xbmc.LOGERROR)
    
    
def infoTrace(module, data):
    log = "VPN Mgr : (" + module + ") " + data
    xbmc.log(msg=log, level=xbmc.LOGNOTICE)

    
def enum(**enums):
    return type('Enum', (), enums)    
    