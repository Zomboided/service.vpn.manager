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
#    This module is a bunch of functions that are called from the settings
#    menu to manage various files groups.

import xbmcaddon
import xbmcgui
import xbmcvfs
import datetime
import os
from libs.vpnproviders import removeGeneratedFiles, cleanPassFiles, providers, usesUserKeys, usesMultipleKeys, getUserKeys
from libs.vpnproviders import getUserCerts, getVPNDisplay, getVPNLocation, refreshFromGit, removeDownloadedFiles
from libs.utility import debugTrace, errorTrace, infoTrace, newPrint
from libs.platform import getLogPath, getUserDataPath, writeVPNLog, copySystemdFiles, addSystemd, removeSystemd, generateVPNs
from libs.common import resetVPNConnections, isVPNConnected, disconnectVPN
from libs.generation import generateAll
from libs.ipinfo import resetIPServices

addon = xbmcaddon.Addon("service.vpn.manager")
addon_name = addon.getAddonInfo("name")

action = sys.argv[1]

debugTrace("-- Entered managefiles.py with parameter " + action + " --")

# Reset the ovpn files
if action == "ovpn":
    if addon.getSetting("1_vpn_validated") == "" or xbmcgui.Dialog().yesno(addon_name, "Resetting the .ovpn files will disconnect and reset all VPN connections. Connections must be re-validated before use. Continue?"):
        # Disconnect so that live files are not being modified
        if isVPNConnected(): resetVPNConnections(addon)            
        debugTrace("Deleting all generated ovpn files")
        # Delete the ovpn files and the generated flag file.
        removeGeneratedFiles()
        # Reset the IP service error counts, etc
        resetIPServices()
        xbmcgui.Dialog().ok(addon_name, "Deleted all .ovpn files. Validate a connection to recreate them.\n")

        
# Generate the VPN provider files
if action == "generate":
    # Only used during development to create location files
    generateAll()
    xbmcgui.Dialog().ok(addon_name, "Regenerated some or all of the VPN location files.\n")        
       

# Delete all of the downloaded VPN files
if action == "downloads":
    debugTrace("Deleting all downloaded VPN files")
    removeDownloadedFiles()
    xbmcgui.Dialog().ok(addon_name, "Deleted all of the downloaded VPN files. They'll be downloaded again if required.\n")

        
# Copy the log file        
elif action == "log":
    log_path = ""
    dest_path = ""
    try:
        log_path = getLogPath()
        start_dir = ""
        dest_folder = xbmcgui.Dialog().browse(0, "Select folder to copy log file into", "files", "", False, False, start_dir, False)
        dest_path = "kodi " + datetime.datetime.now().strftime("%y-%m-%d %H-%M-%S") + ".log"
        dest_path = dest_folder + dest_path.replace(" ", "_")
        # Write VPN log to log before copying
        writeVPNLog()
        debugTrace("Copying " + log_path + " to " + dest_path)
        addon = xbmcaddon.Addon("service.vpn.manager")
        infoTrace("managefiles.py", "Copying log file to " + dest_path + ".  Using version " + addon.getSetting("version_number"))
        xbmcvfs.copy(log_path, dest_path)
        if not xbmcvfs.exists(dest_path): raise IOError('Failed to copy log ' + log_path + " to " + dest_path)
        dialog_message = "Copied log file to:\n" + dest_path
    except:
        errorTrace("Failed to copy log from " + log_path + " to " + dest_path)
        if xbmcvfs.exists(log_path):
            dialog_message = "Error copying log, try copying it to a different location."
        else:
            dialog_messsage = "Could not find the kodi.log file."
        errorTrace("managefiles.py", dialog_message + " " + log_path + ", " + dest_path)
    xbmcgui.Dialog().ok("Log Copy", dialog_message)


# Delete the user key and cert files        
elif action == "user":
    if addon.getSetting("1_vpn_validated") == "" or xbmcgui.Dialog().yesno(addon_name, "Deleting key and certificate files will disconnect and reset all VPN connections. Connections must be re-validated before use. Continue?"):

        # Disconnect so that live files are not being modified
        if isVPNConnected(): resetVPNConnections(addon)
    
        # Select the provider
        provider_list = []
        for provider in providers:
            if usesUserKeys(provider):
                provider_list.append(getVPNDisplay(provider))
        provider_list.sort()
        index = xbmcgui.Dialog().select("Select VPN provider", provider_list)
        provider_display = provider_list[index]
        provider = getVPNLocation(provider_display)
        # Get the key/cert pairs for that provider and offer up for deletion
        user_keys = getUserKeys(provider)
        user_certs = getUserCerts(provider)
        if len(user_keys) > 0 or len(user_certs) > 0:
            still_deleting = True
            while still_deleting:
                if len(user_keys) > 0 or len(user_certs) > 0:
                
                    # Build a list of things to display.  We should always have pairs, but if
                    # something didn't copy or the user has messed with the dir this will cope
                    all_user = []
                    single_pair = "user  [I](Same key and certificate used for all connections)[/I]"
                    for key in user_keys:
                        list_item = os.path.basename(key)
                        list_item = list_item.replace(".key", "")
                        if list_item == "user": list_item = single_pair
                        all_user.append(list_item)
                    for cert in user_certs:
                        list_item = os.path.basename(cert)
                        list_item = list_item.replace(".crt", "")
                        if list_item == "user": list_item = single_pair
                        if not list_item in all_user: all_user.append(list_item)
                    all_user.sort()

                    # Offer a delete all option if there are multiple keys                
                    all_item = "[I]Delete all key and certificate files[/I]"
                    if usesMultipleKeys(provider):
                        all_user.append(all_item)
                        
                    # Add in a finished option
                    finished_item = "[I]Finished[/I]"
                    all_user.append(finished_item)
                    
                    # Get the pair to delete
                    index = xbmcgui.Dialog().select("Select key and certificate to delete, or [I]Finished[/I]", all_user)
                    if all_user[index] == finished_item:
                        still_deleting = False
                    else:
                        if all_user[index] == single_pair : all_user[index] = "user"
                        if all_user[index] == all_item:                        
                            if xbmcgui.Dialog().yesno(addon_name, "Are you sure you want to delete all key and certificate files for " + provider_display + "?"):
                                for item in all_user:
                                    if not item == all_item and not item == finished_item: 
                                        path = getUserDataPath(provider + "/" + item)
                                        try:
                                            if xbmcvfs.exists(path + ".key"):
                                                xbmcvfs.delete(path + ".key")
                                            if xbmcvfs.exists(path + ".txt"):
                                                xbmcvfs.delete(path + ".txt")
                                            if xbmcvfs.exists(path + ".crt"):
                                                xbmcvfs.delete(path + ".crt")
                                        except:
                                            xbmcgui.Dialog().ok(addon_name, "Couldn't delete one of the key or certificate files:\n" + path)
                        else:
                            path = getUserDataPath(provider + "/" + all_user[index])
                            try:
                                if xbmcvfs.exists(path+".key"):
                                    xbmcvfs.delete(path + ".key")
                                if xbmcvfs.exists(path + ".txt"):
                                    xbmcvfs.delete(path + ".txt")
                                if xbmcvfs.exists(path + ".crt"):
                                    xbmcvfs.delete(path + ".crt")
                            except:
                                xbmcgui.Dialog().ok(addon_name, "Couldn't delete one of the key or certificate files:\n" + path)
                            
                        # Fetch the directory list again
                        user_keys = getUserKeys(provider)
                        user_certs = getUserCerts(provider)
                        if len(user_keys) == 0 and len(user_certs) == 0:
                            xbmcgui.Dialog().ok(addon_name, "All key and certificate files for " + provider_display + " have been deleted.")
                else:
                    still_deleting = False
        else:
            xbmcgui.Dialog().ok(addon_name, "No key and certificate files exist for " + provider_display + ".")


xbmc.executebuiltin("Addon.OpenSettings(service.vpn.manager)")    
    
debugTrace("-- Exit managefiles.py --")
