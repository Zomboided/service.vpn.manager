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
#    This module kicks the VPN Manager for OpenVPN background monitor
#    service to get it to re-read the configuration details.

import xbmcgui
import xbmcaddon
from libs.common import updateService
from libs.utility import debugTrace, errorTrace, infoTrace


debugTrace("-- Entered recycle.py --")

# Get info about the addon that this script is pretending to be attached to
addon = xbmcaddon.Addon("service.vpn.manager")
addon_name = addon.getAddonInfo("name")

# Reset the VPN connection values stored in the settings.xml
xbmcgui.Dialog().notification(addon_name, "VPN monitor using updated settings.", xbmcgui.NOTIFICATION_INFO, 3000)
# No need to stop/start monitor, just need to let the monitor know things have changed
infoTrace("recycle.py", "Requested update to service process")
updateService()

xbmc.executebuiltin("Addon.OpenSettings(service.vpn.manager)")

debugTrace("-- Exit recycle.py --")
    