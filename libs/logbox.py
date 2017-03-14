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
#    This module will display a log box on the screen

import xbmcaddon
import xbmcgui
import xbmcvfs
from utility import debugTrace, errorTrace, infoTrace
from platform import getVPNLogFilePath, getLogPath, getImportLogPath, getAddonPath, getUserDataPath


ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92


# Class to display a box with an ok and refresh, a close, and a big pane full of small text
class LogBox(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self.caption = kwargs.get("caption", "")
        self.text = kwargs.get("text", "")
        xbmcgui.WindowXMLDialog.__init__(self)

    def onInit(self):
        self.getControl(100).setLabel(self.caption)
        self.getControl(200).setText(self.text)

    def onAction(self, action):
        actionId = action.getId()
        if actionId in [ACTION_PREVIOUS_MENU, ACTION_NAV_BACK]:
            return self.close()
            

def showLogBox(caption, text):
    path = xbmcaddon.Addon("service.vpn.manager").getAddonInfo("path")
    win = LogBox("logtextbox.xml", path, caption=caption, text=text)
    win.doModal()
    del win
    

def popupKodiLog():
    dialog_text = ""
    log_file = open(getLogPath(), 'r')
    log_output = log_file.readlines()
    log_file.close()    
    for line in log_output:
        dialog_text = dialog_text + line
    showLogBox("Kodi Log", dialog_text)

  
def popupImportLog():
    dialog_text = ""
    if xbmcvfs.exists(getImportLogPath()):
        log_file = open(getImportLogPath(), 'r')
        log_output = log_file.readlines()
        log_file.close()    
        for line in log_output:
            dialog_text = dialog_text + line
    else:
            dialog_text = "No import log file available.  A log file is only available once the import wizard has been run.\n\n"
            dialog_text = dialog_text + "The User Defined directory is " + getUserDataPath("UserDefined/") + "\n\n"
            dialog_text = dialog_text + "More information on using User Defined VPNs can be found on the GitHub wiki for the service.vpn.manager project.\n"
    showLogBox("Import Wizard Log", dialog_text)

    
def popupOpenVPNLog(provider):
    dialog_text = ""
    if xbmcvfs.exists(getVPNLogFilePath()):
        log_file = open(getVPNLogFilePath(), 'r')
        log_output = log_file.readlines()
        log_file.close()
        for line in log_output:
            dialog_text = dialog_text + line
    else:
        dialog_text = dialog_text + "No openvpn log file available.  A log file is only available once an attempt has been made to start a VPN connection.\n"
    showLogBox("OpenVPN Log", dialog_text)    
