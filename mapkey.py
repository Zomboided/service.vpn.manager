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
#    This module allows the user to bind a key to one of the operations
#    that can be performed within VPN Manager

import xbmc
from xbmcgui import Dialog, WindowXMLDialog,DialogProgress
import xbmcgui
import xbmcaddon
import xbmcvfs
import os
import glob
from threading import Timer
from libs.utility import debugTrace, errorTrace, infoTrace, newPrint
from libs.platform import getKeyMapsPath, getKeyMapsFileName, getAddonPath
from libs.common import fixKeymaps, getCycleLock, freeCycleLock, clearVPNCycle


class KeyListener(WindowXMLDialog):
    TIMEOUT = 5

    def __new__(cls):
        gui_api = tuple(map(int, xbmcaddon.Addon('xbmc.gui').getAddonInfo('version').split('.')))
        file_name = "DialogNotification.xml" if gui_api >= (5, 11, 0) else "DialogKaiToast.xml"
        return super(KeyListener, cls).__new__(cls, file_name, "")
        
    def __init__(self):
        self.key = None

    def onInit(self):
        self.getControl(400).setImage(getAddonPath(True, "/resources/map.png"))
        self.getControl(401).addLabel(xbmcaddon.Addon("service.vpn.manager").getAddonInfo("name"))
        self.getControl(402).addLabel("Press a key to map or wait to clear.")

    def onAction(self, action):
        code = action.getButtonCode()
        self.key = None if code == 0 else str(code)
        self.close()
        
    @staticmethod
    def record_key():
        dialog = KeyListener()
        timeout = Timer(KeyListener.TIMEOUT, dialog.close)
        timeout.start()
        dialog.doModal()
        timeout.cancel()
        key = dialog.key
        del dialog
        if key == None: return ""
        return key
        
        
addon = xbmcaddon.Addon("service.vpn.manager")
addon_name = addon.getAddonInfo("name")

action = sys.argv[1]

debugTrace("-- Entered mapkey.py with parameter " + action + " --")

cycle_key = ""
table_key = ""
table_long = False
info_key = ""

map_name = getKeyMapsFileName()
xml_start = '<keymap><global><keyboard>\n'
xml_key = '<key id="#KEY">runscript(#PATH#COMMAND)</key>\n'
xml_long = '<key id="#KEY" mod="longpress">runscript(#PATH#COMMAND)</key>\n'
xml_end = '</keyboard></global></keymap>\n'
cycle_command = "cycle.py"
table_command = "table.py"
info_command = "infopopup.py"

# Fix the keymap if it's been renamed by the Keymap addon
fixKeymaps()

lines = []

# Read any existing keymap and the keys we're interested in
if xbmcvfs.exists(getKeyMapsPath(map_name)):
    path = getKeyMapsPath(map_name)    
    try:
        debugTrace("Writing the map file to " + path)
        map_file = open(path, 'r')
        lines = map_file.readlines()
        map_file.close()
        i = 0
        for line in lines:
            if cycle_command in line:
                i1 = line.index("key id=\"") + 8
                i2 = line.index("\"", i1)
                cycle_key = line[i1:i2]
                debugTrace("Found cycle key " + cycle_key)
                lines[i] = ""
            if table_command in line:
                i1 = line.index("key id=\"") + 8
                i2 = line.index("\"", i1)
                table_key = line[i1:i2]
                debugTrace("Found table key " + table_key)
                if 'mod="longpress"' in line: table_long = True
                lines[i] = ""
            if info_command in line:
                i1 = line.index("key id=\"") + 8
                i2 = line.index("\"", i1)
                info_key = line[i1:i2]
                debugTrace("Found infopopup key " + info_key)
                lines[i] = ""
            i = i + 1
    except Exception as e:
        errorTrace("mapkey.py", map_name + " is malformed")
        errorTrace("mapkey.py", str(e))
        lines = []


# If there is no keymap, create a blank one with start and end tags
if len(lines) == 0:
    lines.append(xml_start)
    lines.append(xml_end)

if getCycleLock():

    clearVPNCycle()

    # Get the updated keys
    if action == "cycle":
        if cycle_key == "": 
            msg = "Do you want to map a key or remote button to the VPN cycle function?"
            y = "No"
            n = "Yes"
        else: 
            msg = "Key ID " + cycle_key + " is mapped to the VPN cycle function.  Remap or clear current mapping?"
            y = "Clear"
            n = "Remap"
        if not xbmcgui.Dialog().yesno(addon_name, msg, "", "", n, y):
            cycle_key = KeyListener().record_key()
            if cycle_key == "": 
                dialog = "VPN cycle is not mapped to a key."
                icon = "/resources/unmapped.png"
            else: 
                dialog = "VPN cycle is mapped to key ID " + cycle_key + "."
                icon = "/resources/mapped.png"
            xbmcgui.Dialog().notification(addon_name, dialog, getAddonPath(True, icon), 5000, False)
        else:
            if not cycle_key == "": 
                cycle_key = ""

    if action == "table":
        if table_key == "": 
            msg = "Do you want to map a key or remote button to the VPN connection table function?"
            y = "No"
            n = "Yes"
        else: 
            msg = "Key ID " + table_key + " is mapped to the VPN connection table function.  Remap or clear current mapping?"
            y = "Clear"
            n = "Remap"
        if not xbmcgui.Dialog().yesno(addon_name, msg, "", "", n, y):
            if not cycle_key == "" and xbmcgui.Dialog().yesno(addon_name, "Do you want to map a long press of the current cycle key to bring up a list of connections?. [I]This is only recommended for keyboard usage, not remote controls.[/I]", "", "", "No", "Yes"):
                table_key = cycle_key
            else:
                table_key = KeyListener().record_key()
                table_long = False
                if table_key == "": 
                    dialog = "VPN connection table is not mapped to a key."
                    icon = "/resources/unmapped.png"
                else: 
                    dialog = "VPN connection table is mapped to key ID " + cycle_key + "."
                    icon = "/resources/mapped.png"
                    if xbmcgui.Dialog().yesno(addon_name, "Do you want display the list of all connections (with protocol filter applied) or just those validated?.  You can change this later in the Settings/Monitor menu.", "", "", "Validated", "All"):
                        addon.setSetting("table_display_type", "All Connections")
                    else:
                        addon.setSetting("table_display_type", "Validated Connections")
                xbmcgui.Dialog().notification(addon_name, dialog, getAddonPath(True, icon), 5000, False)
        else:
            if not table_key == "": 
                table_key = ""           
                   
    if action == "info":
        if info_key == "": 
            msg = "Map a key or remote button to the information display function?"
            y = "No"
            n = "Yes"
        else: 
            msg = "Key ID " + info_key + " is mapped to the information display function.  Remap or clear current mapping?"
            y = "Clear"
            n = "Remap"
        if not xbmcgui.Dialog().yesno(addon_name, msg, "", "", n, y):
            info_key = KeyListener().record_key()
            if info_key == "": 
                dialog = "Info display is not mapped to a key."
                icon = "/resources/unmapped.png"
            else: 
                dialog = "Info display is mapped to key ID " + info_key + "."
                icon = "/resources/mapped.png"
            xbmcgui.Dialog().notification(addon_name, dialog, getAddonPath(True, icon), 5000, False)
        else:
            if not info_key == "":
                info_key = ""
    
    
    # Add the keys to the start of the keymap file
    if not cycle_key == "":
        out = xml_key.replace("#KEY", cycle_key)
        out = out.replace("#PATH", getAddonPath(True, ""))
        out = out.replace("#COMMAND", cycle_command)
        lines.insert(1, out)
    if not table_key == "":
        if cycle_key == table_key or table_long:
            out = xml_long.replace("#KEY", table_key)
        else:
            out = xml_key.replace("#KEY", table_key)
            out = out.replace("#PATH", getAddonPath(True, ""))
            out = out.replace("#COMMAND", table_command)
        lines.insert(1, out)
    if not info_key == "":
        out = xml_key.replace("#KEY", info_key)
        out = out.replace("#PATH", getAddonPath(True, ""))
        out = out.replace("#COMMAND", info_command)
        lines.insert(1, out)
    

    # Count the number of valid lines to write out
    i = 0
    for line in lines:
        if not line == "": i += 1
    
    try:    
        path = getKeyMapsPath(map_name)
        if i == 2:
            # Delete keymap file, it's empty apart from the start and end tags
            if xbmcvfs.exists(path):
                debugTrace("No key mappings so deleting the map file " + path)            
                xbmcvfs.delete(path)
                xbmcgui.Dialog().ok(addon_name, "Keymap has been removed as no keys have been mapped.  You must restart for these changes to take effect.")
            else:
                debugTrace("No key mappings so not creating a map file")
        else:
            # Write the updated keymap
            path = getKeyMapsPath(map_name)
            map_file = open(path, 'w')
            for line in lines:
                if not line == "": map_file.write(line)    
            map_file.close()
            xbmcgui.Dialog().ok(addon_name, "Keymap has been updated.  You must restart for these changes to take effect.")
    except Exception as e:
        errorTrace("mapkey.py", "Couldn't update keymap file " + path)
        errorTrace("mapkey.py", str(e))
        xbmcgui.Dialog().ok(addon_name, "Problem updating the keymap file, check error log.")
        
    # Warn the user if maps could clash
    path = getKeyMapsPath("*.xml")
    try:
        debugTrace("Getting contents of keymaps directory " + path)
        files = (glob.glob(path))
        if len(files) > 1:
            xbmcgui.Dialog().ok(addon_name, "Other keymaps exist and are applied in alphabetical order.  If your mappings don't work then it could be that they're being over written by another map.")
            infoTrace("mapkey.py", "Multiple (" + str(len(files)) + ") keymaps, including " + map_name + " detected in " + getKeyMapsPath(""))
    except Exception as e:
        errorTrace("import.py", "Couldn't check to see if other keymaps were clashing")
        errorTrace("import.py", str(e))

freeCycleLock()

xbmc.executebuiltin("Addon.OpenSettings(service.vpn.manager)")

debugTrace("-- Exit mapkey.py --")