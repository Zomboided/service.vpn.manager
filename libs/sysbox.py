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
#    This module will display a system info box on the screen

import xbmcaddon
import xbmcgui
from libs.common import getSystemData
from libs.utility import debugTrace, errorTrace, infoTrace, getID
from libs.vpnplatform import getVPNLogFilePath, getLogPath, getImportLogPath, getAddonPath, getUserDataPath

ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92


# Class to display two columns of text with an ok, and a close
class InfoBox(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self.caption = kwargs.get("caption", "")
        self.text_left = kwargs.get("text_left", "")
        self.text_right = kwargs.get("text_right", "")
        xbmcgui.WindowXMLDialog.__init__(self)

    def onInit(self):
        self.getControl(100).setLabel(self.caption)
        self.getControl(200).setText(self.text_left)
        self.getControl(300).setText(self.text_right)

    def onAction(self, action):
        actionId = action.getId()
        if actionId in [ACTION_PREVIOUS_MENU, ACTION_NAV_BACK]:
            return self.close()
        

def showInfoBox(caption, text_l, text_r):
    path = xbmcaddon.Addon(getID()).getAddonInfo("path")
    win = InfoBox("infotextbox.xml", path, caption=caption, text_left=text_l, text_right=text_r)
    win.doModal()
    del win
    

def popupSysBox():
    if not getID() == "":
        addon = xbmcaddon.Addon(getID())
        dialog_text_l = ""
        dialog_text_r = ""
        data_left = getSystemData(addon, True, True, False, False)
        data_right = getSystemData(addon, False, False, False, True)
        for line in data_left:
            if line.startswith("[B]") and not dialog_text_l == "": dialog_text_l = dialog_text_l + "\n"
            dialog_text_l = dialog_text_l + line + "\n"
        for line in data_right:
            if line.startswith("[B]") and not dialog_text_r == "": dialog_text_r = dialog_text_r + "\n"
            dialog_text_r = dialog_text_r + line + "\n"    
        showInfoBox("System Information", dialog_text_l, dialog_text_r)
    else:
        errorTrace("sysbox.py", "VPN service is not ready")
    