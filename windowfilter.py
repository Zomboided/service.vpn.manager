#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#    Copyright (C) 2016 Zomboided
#
#    Connection script called by the VPN Manager for OpenVPN settings screen
#    to validate a connection to a VPN provider.
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
#    This module deals with the setting, editing and removal of window filters

import xbmc
import xbmcaddon
import xbmcgui
from libs.utility import debugTrace, errorTrace, infoTrace, newPrint


def editRange(default):
    # Ask user for range of window IDs and return "low-high" if value or "" if invalid
    default_low = ""
    default_high = ""
    if not default == "":
        default_low, default_high = default.split("-")
    new_filter_low = xbmcgui.Dialog().numeric(0, "Enter first window ID of range", default_low)
    new_filter_high = xbmcgui.Dialog().numeric(0, "Enter last window ID of range", default_high)
    if (not(new_filter_low == "" or new_filter_high == "")) and (int(new_filter_low) < int(new_filter_high)) and int(new_filter_low) > 9999 and int(new_filter_high) < 100000:
        return new_filter_low + "-" + new_filter_high
    else:
        xbmcgui.Dialog().ok(addon_name, "Range is invalid.  IDs should be 5 characters and the first ID should be less than the second ID.")
        return ""

        
def editSingle(default):
    new_filter = xbmcgui.Dialog().numeric(0, "Enter window ID", default)
    if (not new_filter == "") and int(new_filter) > 9999 and int(new_filter) < 100000:
        return new_filter
    else:
        xbmcgui.Dialog().ok(addon_name, "ID is invalid.  IDs should be 5 characters")
        return ""
       

id_range = "[I]Add range of IDs[/I]"
id_single = "[I]Add single ID[/I]"
id_reset = "[I]Delete all[/I]"
id_cancel = "[I]Cancel changes[/I]"
id_done = "[I]Done[/I]"

addon = xbmcaddon.Addon("service.vpn.manager")
addon_name = addon.getAddonInfo("name")

vpn = sys.argv[1]

debugTrace("-- Entered windowfilter.py with parameter " + vpn + " --")

show_filters = True

# Build the list of filters
if vpn == "0":
    filter_string = addon.getSetting("vpn_excluded_windows")
else:
    filter_string = addon.getSetting(vpn + "_vpn_windows")

if not filter_string == "":
    filters = filter_string.split(",")
else:
    filters = []

# And add options to the filters.  Cancel is last as pressing escape is like selecting the last option    
filters.append(id_single)
filters.append(id_range)
filters.append(id_reset)
filters.append(id_done)
filters.append(id_cancel)

if vpn == "1" : vpnth = " first"
if vpn == "2" : vpnth = " second"
if vpn == "3" : vpnth = " third"
if vpn == "4" : vpnth = " fourth"
if vpn == "5" : vpnth = " fifth"
if vpn == "6" : vpnth = " sixth"
if vpn == "7" : vpnth = " seventh"
if vpn == "8" : vpnth = " eighth"
if vpn == "9" : vpnth = " ninth"
if vpn == "10" : vpnth = " tenth"

if vpn == "0":
    title = "Windows not using a VPN"
else:
    title = "Windows using " + vpnth + " VPN"

# Loop around edits until done or cancel are selected
while show_filters:
 
    i = xbmcgui.Dialog().select(title, filters)

    if filters[i] == id_done:
        # Make the filters into a single string and store it
        output_filter = ""
        if len(filters) > 5:
            for i in range (0, (len(filters)-5)):
                if i > 0 : output_filter = output_filter + ","
                output_filter = output_filter + filters[i]
        if vpn == "0":
            addon.setSetting("vpn_excluded_windows", output_filter)
        else:
            addon.setSetting(vpn + "_vpn_windows", output_filter)        
        show_filters = False
    elif filters[i] == id_cancel:
        # Don't commit the changes, just exit loop and return to settings
        show_filters = False
    elif filters[i] == id_reset:
        # Delete all of the filters
        if len(filters) > 5:
            del filters[0:len(filters)-5]
    elif filters[i] == id_single:
        # Ask user for window ID
        new_filter = editSingle("")
        if not new_filter == "": filters.insert(len(filters)-5, new_filter)
    elif filters[i] == id_range:
        # Ask user for range of window IDs
        new_filter = editRange("")
        if not new_filter == "": filters.insert(len(filters)-5, new_filter)
    else:
        # Edit or delete an existing filter
        if not xbmcgui.Dialog().yesno(addon_name, "Edit or delete window ID filter " + filters[i] + "?", "", "", "Edit", "Delete"):
            if "-" in filters[i]:
                new_filter = editRange(filters[i])
            else:
                new_filter = editSingle(filters[i])
            if not new_filter == "": filters.insert(len(filters)-5, new_filter)
        else:
            del filters[i]

xbmc.executebuiltin("Addon.OpenSettings(service.vpn.manager)")    
    
debugTrace("-- Exit windowfilter.py --")
