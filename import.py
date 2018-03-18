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
#    This module assists with the import of a user defined VPN provider

import xbmc
from libs.utility import debugTrace, errorTrace, infoTrace, newPrint, getID
from libs.userdefined import importWizard

debugTrace("Entered import.py")

if not getID() == "":     
    importWizard()        

    # Return to the settings screen
    command = "Addon.OpenSettings(" + getID() + ")"
    xbmc.executebuiltin(command)
else:
    errorTrace("import.py", "VPN service is not ready")

debugTrace("Exit import.py")
