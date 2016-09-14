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
#    This module update the boot process for the underlying OS to try
#    and connect to the first VPN before Kodi boots.

import xbmcgui
import xbmcaddon
from libs.utility import debugTrace

action = sys.argv[1]

debugTrace("-- Entered updateboot.py with parameter " + action + " --")

# Get info about the addon that this script is pretending to be attached to
addon = xbmcaddon.Addon("service.vpn.manager")
addon_name = addon.getAddonInfo("name")

# <FIXME> Work out what to do here
if xbmcgui.Dialog().yesno(addon_name, action + " boot settings"):
    i = 1     

    

xbmc.executebuiltin("Addon.OpenSettings(service.vpn.manager)")      
    
debugTrace("-- Exit updateboot.py --")    