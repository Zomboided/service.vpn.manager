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
#    This module pops up a screen with some log info.

import xbmcaddon
import xbmcgui
from libs.utility import debugTrace, errorTrace, infoTrace
from libs.logbox import popupOpenVPNLog, popupKodiLog, popupImportLog

action = sys.argv[1]

debugTrace("-- Entered infopopup.py with parameter " + action + " --")

if action == "kodi":
    popupKodiLog()

if action == "openvpn":
    popupOpenVPNLog("")
    
if action == "import":
    popupImportLog()

debugTrace("-- Exit infopopup.py --")
