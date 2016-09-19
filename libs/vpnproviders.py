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
#    VPN provider code used by the VPN Manager for OpenVPN add-on.

import xbmc
import xbmcgui
import xbmcvfs
import xbmcaddon
import glob
from libs.utility import debugTrace, errorTrace, infoTrace
from libs.platform import getAddonPath, getUserDataPath, fakeConnection, getSeparator, getPlatform, platforms


# **** ADD MORE VPN PROVIDERS HERE ****
# Display names for each of the providers (matching the guff in strings.po)
provider_display = ["Private Internet Access", "IPVanish", "VyperVPN", "Invisible Browsing VPN", "NordVPN", "tigerVPN", "Hide My Ass", "PureVPN", "LiquidVPN", "AirVPN", "CyberGhost", "Perfect Privacy", "TorGuard", "User Defined", "LimeVPN", "HideIPVPN", "VPN Unlimited", "Hide.Me", "BTGuard", "ExpressVPN", "SaferVPN", "Celo", "VPN.ht", "TotalVPN", "WiTopia", "proXPN", "IVPN", "SecureVPN.to", "VPNSecure", "RA4W VPN"]

# **** ADD MORE VPN PROVIDERS HERE ****
# Directory names for each of the providers (in the root of the addon)
# Must be in the same order as the provider display name above
providers = ["PIA", "IPVanish", "VyprVPN", "ibVPN", "NordVPN", "tigerVPN", "HMA", "PureVPN", "LiquidVPN", "AirVPN", "CyberGhost", "PerfectPrivacy", "TorGuard", "UserDefined", "LimeVPN", "HideIPVPN", "VPNUnlimited", "HideMe", "BTGuard", "ExpressVPN", "SaferVPN", "Celo", "VPN.ht", "TotalVPN", "WiTopia", "proXPN", "IVPN", "SecureVPN", "VPNSecure", "RA4WVPN"]

# **** ADD VPN PROVIDERS HERE IF THEY USE A KEY ****
# List of providers which use user keys and certs, either a single one, or one per connection
# Names must match the directory names as used in providers, just above
providers_with_multiple_keys = ["PerfectPrivacy", "Celo", "SecureVPN"]
providers_with_single_keys = ["AirVPN", "CyberGhost", "HMA", "HideIPVPN", "VPNUnlimited", "ExpressVPN", "WiTopia", "VPNSecure"]

# *** ADD VPN PROVIDERS HERE IF THEY DON'T USE USERNAME AND PASSWORD ****
# List of providers which don't use auth-user-pass.
# Names must match the directory names as used in providers, just above
providers_no_pass = ["AirVPN", "VPNUnlimited", "ExpressVPN", "WiTopia", "VPNSecure"]

# Leave this alone...it must match the text in providers
user_def_disp_str = "User Defined"
user_def_str = "UserDefined"
        
def getAddonPathWrapper(path):
    # This function resets the VPN profiles to the standard VPN Manager install
    # location as per OpenELEC, or to the platform install location
    force_default_install = fakeConnection()
    if force_default_install:
        return "/storage/.kodi/addons/service.vpn.manager/" + path        
    else:
        if getPlatform() == platforms.WINDOWS:
            return getAddonPath(True, path).replace("\\", "\\\\")
        else:
            return getAddonPath(True, path)


def getUserDataPathWrapper(path):
    # This function resets the VPN profiles to the standard VPN Manager install
    # location as per OpenELEC, or to the platform install location
    force_default_install = fakeConnection()
    if force_default_install:
        return "/storage/.kodi/userdata/addon_data/service.vpn.manager/" + path        
    else:
        if getPlatform() == platforms.WINDOWS:
            return getUserDataPath(path).replace("\\", "\\\\")
        else:
            return getUserDataPath(path)
        
                
def getVPNLocation(vpn_provider):
    # This function translates between the display name and the directory name
    i=0
    for provider in provider_display:
        if vpn_provider == provider: return providers[i]
        if vpn_provider == providers[i]: return providers[i]
        i = i + 1
    return ""

    
def getVPNDisplay(vpn_provider):    
    # This function translates between the directory name and the display name
    i=0
    for provider in providers:
        if vpn_provider == provider: return provider_display[i]
        i = i + 1
    return vpn_provider
    

def getAddonList(vpn_provider, filter):
    # Return the list of ovpn files for a given provider (aka directory name...)
    path = getAddonPath(True, getVPNLocation(vpn_provider) + "/" + filter)
    debugTrace("Getting list of profiles in " + path)
    return sorted(glob.glob(path))  

    
def getUserDataList(vpn_provider, filter):    
    # Return all user files for a provider (aka directory name...)
    path = getUserDataPath(getVPNLocation(vpn_provider) + "/" + filter)
    debugTrace("Getting list of files in " + path)
    return sorted(glob.glob(path))  
    

def usesUserKeys(vpn_provider):
    if usesSingleKey(vpn_provider): return True
    if usesMultipleKeys(vpn_provider): return True
    return False
    
    
def usesSingleKey(vpn_provider):
    if isUserDefined(vpn_provider):
        if xbmcaddon.Addon("service.vpn.manager").getSetting("user_def_keys") == "Single": return True
    if vpn_provider in providers_with_single_keys: return True
    return False

    
def usesMultipleKeys(vpn_provider):
    if isUserDefined(vpn_provider):
        if xbmcaddon.Addon("service.vpn.manager").getSetting("user_def_keys") == "Multiple": return True
    if vpn_provider in providers_with_multiple_keys: return True
    return False
    

def getUserKeys(vpn_provider):
    # Return the list of key and cert files for a given provider (aka directory name...)
    path = getUserDataPath(getVPNLocation(vpn_provider)+"/*.key")
    debugTrace("Getting key files " + path)
    return (glob.glob(path))         

    
def getUserCerts(vpn_provider):
    # Return the list of key and cert files for a given provider (aka directory name...)
    path = getUserDataPath(getVPNLocation(vpn_provider)+"/*.crt")
    debugTrace("Getting certificate files " + path)
    return (glob.glob(path))         
    
    
def gotKeys(vpn_provider, ovpn_name):
    # Check to see if we have the key for this connection.  If this provider just uses
    # a single key then the getKey/CertName piece will work this out.  If no key is passed
    # in then we'll just report whether or not any keys exist for this provider
    if not ovpn_name == "":
        key_name = getUserDataPath(vpn_provider + "/" + getKeyName(vpn_provider, ovpn_name))
        cert_name = getUserDataPath(vpn_provider + "/" + getCertName(vpn_provider, ovpn_name))
        debugTrace("Checking for user key " + key_name)
        debugTrace("Checking for user cert " + cert_name)
        if xbmcvfs.exists(key_name) and xbmcvfs.exists(cert_name): return True
        debugTrace("One of the user key and cert files did not exist")
        return False
    else:
        return False
    
    
def copyKeyAndCert(vpn_provider, ovpn_name, user_key, user_cert):
    # Copy the user key and cert to the userdata directory
    key_dest = getUserDataPath(vpn_provider + "/" + getKeyName(vpn_provider, ovpn_name))
    key_source = user_key
    cert_dest = getUserDataPath(vpn_provider + "/" + getCertName(vpn_provider, ovpn_name))
    cert_source = user_cert
    try:
        debugTrace("Copying key " + key_source + " to " + key_dest)
        if xbmcvfs.exists(key_dest): xbmcvfs.delete(key_dest)
        xbmcvfs.copy(key_source, key_dest)
        debugTrace("Copying cert " + cert_source + " to " + cert_dest)
        if xbmcvfs.exists(cert_dest): xbmcvfs.delete(cert_dest)
        xbmcvfs.copy(cert_source, cert_dest)
        return True
    except:
        errorTrace("vpnproviders.py", "Failed to copy user key or cert file to userdata")
        return False
    

def getKeyName(vpn_provider, ovpn_name):
    # Determines the user key name based on the provider
    if usesSingleKey(vpn_provider):
        return "user.key"
    if usesMultipleKeys(vpn_provider):
        return "user_" + ovpn_name.replace(" ", "_") + ".key"
    return ""


def getCertName(vpn_provider, ovpn_name):
    # Determines the user cert name based on the provider
    if usesSingleKey(vpn_provider):
        return "user.crt"
    if usesMultipleKeys(vpn_provider):
        return "user_" + ovpn_name.replace(" ", "_") + ".crt"
    return ""
        

def usesPassAuth(vpn_provider):
    # Determine if we're using a user name and password or not
    if isUserDefined(vpn_provider):
        if not (xbmcaddon.Addon("service.vpn.manager").getSetting("user_def_credentials") == "true"): 
            return False
    elif vpn_provider in providers_no_pass: return False
    return True

    
def getRegexPattern():
    # Return a regex expression to make a file name look good.
    return r'(?s).*/(.*).ovpn'

    
def cleanPassFiles():
    # Delete the pass.txt file from all of the VPN provider directorys
    for provider in providers:
        filename = getAddonPath(True, provider + "/pass.txt")
        if xbmcvfs.exists(filename) : xbmcvfs.delete(filename)   


def cleanGeneratedFiles():
    # Delete the GENERATED.txt file from all of the VPN provider directorys    
    for provider in providers:
        filename = getAddonPath(True, provider + "/GENERATED.txt")
        if xbmcvfs.exists(filename) : xbmcvfs.delete(filename)         


def removeGeneratedFiles():
    for provider in providers:
        if ovpnGenerated(provider):
            if isUserDefined(provider):
                # If this is the user defined provider, delete everything
                files = getAddonList(provider, "*")
            else:
                # If this is a regular provider, delete just the ovpn files
                files = getAddonList(provider, "*.ovpn")    
            for file in files:
                xbmcvfs.delete(file)
        filename = getAddonPath(True, provider + "/GENERATED.txt")
        if xbmcvfs.exists(filename) : xbmcvfs.delete(filename)             

        
def ovpnFilesAvailable(vpn_provider):
    if xbmcvfs.exists(getAddonPath(True, vpn_provider + "/GENERATED.txt")): return True
    return False

    
def ovpnGenerated(vpn_provider):
    if isUserDefined(vpn_provider): return True
    if xbmcvfs.exists(getAddonPath(True, vpn_provider + "/TEMPLATE.txt")): return True
    return False

    
def isUserDefined(vpn_provider):
    if vpn_provider == user_def_str or vpn_provider == user_def_disp_str: return True
    return False
    
    
def getLocationFiles(vpn_provider):
    # Return the locations files, add any user version to the end of the list
    locations = glob.glob(getAddonPath(True, vpn_provider + "/LOCATIONS*.txt"))
    user_locations = getUserDataPath(vpn_provider + "/LOCATIONS.txt")
    if xbmcvfs.exists(user_locations): locations.append(user_locations.replace(".txt", " User.txt"))
    return locations
    

def fixOVPNFiles(vpn_provider, alternative_locations_name):
    debugTrace("Fixing OVPN files for " + vpn_provider + " using list " + alternative_locations_name)
    # Generate or update the VPN files
    if ovpnGenerated(vpn_provider):
        if not isUserDefined(vpn_provider):
            return generateOVPNFiles(vpn_provider, alternative_locations_name)
        else:
            # User Defined provider is a special case.  The files are copied from
            # userdata rather than generated as such, followed by an update (if needed)
            if copyUserDefinedFiles():
                return updateVPNFiles(vpn_provider)
    else:
        return updateVPNFiles(vpn_provider)
    
    
def generateOVPNFiles(vpn_provider, alternative_locations_name):
    # Generate the OVPN files for a VPN provider using the template and update with location info
    
    infoTrace("vpnproviders.py", "Generating OVPN files for " + vpn_provider + " using list " + alternative_locations_name)

    # See if there's a port override going on
    addon = xbmcaddon.Addon("service.vpn.manager")
    if addon.getSetting("default_udp") == "true":
        portUDP = ""
    else:
        portUDP = addon.getSetting("alternative_udp_port")
        
    if addon.getSetting("default_tcp") == "true":
        portTCP = ""
    else:
        portTCP = addon.getSetting("alternative_tcp_port")

    # Get the logging level
    verb_value = addon.getSetting("openvpn_verb")
    if verb_value == "":
        verb_value = "1"
        addon.setSetting("openvpn_verb", verb_value)
        
    # Load ovpn template
    try:
        debugTrace("Opening template file for " + vpn_provider)
        template_file = open(getAddonPath(True, vpn_provider + "/TEMPLATE.txt"), 'r')
        debugTrace("Opened template file for " + vpn_provider)
        template = template_file.readlines()
        template_file.close()
    except:
        errorTrace("vpnproviders.py", "Couldn't open the template file for " + vpn_provider)
        return False
    
    if getPlatform() == platforms.WINDOWS and addon.getSetting("block_outside_dns") == "true":
        template.append("block-outside-dns")
    
    # Load locations file
    if not alternative_locations_name == "":
        if alternative_locations_name == "User":
            locations_name = getUserDataPath(vpn_provider + "/LOCATIONS.txt")
        else:
            locations_name = getAddonPath(True, vpn_provider + "/LOCATIONS " + alternative_locations_name + ".txt")
    else:
        locations_name = getAddonPath(True, vpn_provider + "/LOCATIONS.txt")

    try:
        debugTrace("Opening locations file for " + vpn_provider + "\n" + locations_name)
        locations_file = open(locations_name, 'r')
        debugTrace("Opened locations file for " + vpn_provider)
        locations = locations_file.readlines()
        locations_file.close()
    except:
        errorTrace("vpnproviders.py", "Couldn't open the locations file for " + vpn_provider + "\n" + locations_name)
        return False

    # For each location, generate an OVPN file using the template
    for location in locations:
        try:
            location_values = location.split(",")
            geo = location_values[0]
            servers = location_values[1].split()
            proto = location_values[2]
            ports = (location_values[3].strip(' \t\n\r')).split()
            port = ""

            # Initialise the set of values that can be modified by the location file tuples
            ca_cert = "ca.crt"
            ta_key = "ta.key"
            crl_pem = "crl.pem"
            dh_parm = "dh.pem"
            user_key = getUserDataPathWrapper(vpn_provider + "/" + getKeyName(vpn_provider, geo))
            user_cert = getUserDataPathWrapper(vpn_provider + "/" + getCertName(vpn_provider, geo))
            remove_flags = ""
            
            if len(location_values) > 4: 
                # The final location value is a list of multiple x=y declarations.
                # These need to be parsed out and modified.
                modifier_tuples = (location_values[4].strip(' \t\n\r')).split()
                # Loop through all of the values splitting them into name value pairs
                for modifier in modifier_tuples:
                    pair = modifier.split("=")
                    if "#CERT" in pair[0]: ca_cert = pair[1].strip()
                    if "#REMOVE" in pair[0]: remove_flags = pair[1].strip()
                    if "#TLSKEY" in pair[0]: ta_key = pair[1].strip()
                    if "#USERKEY" in pair[0]: user_key = pair[1].strip()
                    if "#USERCERT" in pair[0]: user_cert = pair[1].strip()
                    if "#CRLVERIFY" in pair[0]: crl_pem = pair[1].strip()
                    if "#DH" in pair[0]: dh_parm = pair[1].strip()
            if proto == "udp" and not portUDP == "": port = portUDP
            if proto == "tcp" and not portTCP == "": port = portTCP
            if port == "" and len(ports) == 1: port = ports[0]
        except:
            errorTrace("vpnproviders.py", "Location file for " + vpn_provider + " invalid on line\n" + location)
            return False
            
        try:
            ovpn_file = open(getAddonPath(True, vpn_provider + "/" + geo + ".ovpn"), 'w')
            if proto == "tcp":
                servprot = "tcp-client"
            else:
                servprot = proto

            # Do a replace on the tags in the template with data from the location file
            for line in template:
                output_line = line.strip(' \t\n\r')
                # Must check to see if there's a remove tag on the line before looking for other tags
                if "#REMOVE" in output_line:
                    if output_line[output_line.index("#REMOVE")+7] in remove_flags:
                        # Remove the line if it's a flag this location doesn't care about
                        output_line = ""
                    else:
                        # Delete the tag if this location doesn't want this line removed
                        output_line = output_line.replace("#REMOVE" + output_line[output_line.index("#REMOVE")+7], "")
                output_line = output_line.replace("#PROTO", proto)
                output_line = output_line.replace("#SERVPROT", servprot)
                # If there are multiple servers then we'll need to duplicate the server
                # line (which starts with 'remote ') and fix the server.  The rest of the
                # code will deal with the port which is the same for all lines (although
                # this assumption might not be true for all VPN providers...)
                if output_line.startswith("remote "):
                    server_template = output_line
                    server_lines = ""
                    i = 0
                    for server in servers:
                        if not server_lines == "" : server_lines = server_lines + "\n"
                        server_lines = server_lines + server_template.replace("#SERVER", server)
                        if port == "":
                            server_lines = server_lines.replace("#PORT", ports[i])
                        i = i + 1
                    output_line = server_lines
                # There might be other places we use server and port, so still the do the replace
                output_line = output_line.replace("#SERVER", servers[0])
                output_line = output_line.replace("#PORT", port)
                output_line = output_line.replace("#PASS", getAddonPathWrapper(vpn_provider + "/" + "pass.txt"))
                output_line = output_line.replace("#CERT", getAddonPathWrapper(vpn_provider + "/" + ca_cert))
                output_line = output_line.replace("#TLSKEY", getAddonPathWrapper(vpn_provider + "/" + ta_key))
                output_line = output_line.replace("#CRLVERIFY", getAddonPathWrapper(vpn_provider + "/" + crl_pem))
                output_line = output_line.replace("#DH", getAddonPathWrapper(vpn_provider + "/" + dh_parm))
                output_line = output_line.replace("#USERKEY", user_key)
                output_line = output_line.replace("#USERCERT", user_cert)
                output_line = output_line.replace("#PATH", getAddonPathWrapper(vpn_provider + "/"))
                # Overwrite the verb value with the one in the settings
                if output_line.startswith("verb "):
                    output_line = "verb " + verb_value
                # This is a little hack to remove a tag that doesn't work with TCP but is needed for UDP
                # Could do this with a #REMOVE, but doing it here is less error prone.
                if "explicit-exit-notify" in line and proto == "tcp": output_line = ""
                if not output_line == "" : ovpn_file.write(output_line + "\n")
            ovpn_file.close()
            debugTrace("Wrote location " + geo + " " + proto)
        except:
            errorTrace("vpnproviders.py", "Can't write a location file for " + vpn_provider + " failed on line\n" + location)
            return False
    
    # Flag that the files have been generated
    writeGeneratedFile(vpn_provider)

    return True
    
    
def updateVPNFiles(vpn_provider):
    # If the OVPN files aren't generated then they need to be updated with location info    
    
    infoTrace("vpnproviders.py", "Updating VPN profiles for " + vpn_provider)
    # Get the list of VPN profile files        
    ovpn_connections = getAddonList(vpn_provider, "*.ovpn")

    # See if there's a port override going on
    addon = xbmcaddon.Addon("service.vpn.manager")
    if addon.getSetting("default_udp") == "true":
        portUDP = ""
    else:
        portUDP = addon.getSetting("alternative_udp_port")
        
    if addon.getSetting("default_tcp") == "true":
        portTCP = ""
    else:
        portTCP = addon.getSetting("alternative_tcp_port")

    # Get the logging level
    verb_value = addon.getSetting("openvpn_verb")
    if verb_value == "":
        verb_value = "1"
        addon.setSetting("openvpn_verb", verb_value)
        
    for connection in ovpn_connections:
        try:
            f = open(connection, 'r+')
            debugTrace("Processing file " + connection)
            lines = f.readlines()
            f.seek(0)
            f.truncate()
            # Get the profile friendly name in case we need to generate key/cert names
            name = connection[connection.rfind(getSeparator())+1:connection.rfind(".ovpn")]
            
            if getPlatform() == platforms.WINDOWS and addon.getSetting("block_outside_dns") == "true":
                lines.append("block-outside-dns")
            
            # Update the necessary values in the ovpn file
            for line in lines:
                
                # Update path to pass.txt
                if not isUserDefined(vpn_provider) or addon.getSetting("user_def_credentials") == "true":
                    if line.startswith("auth-user-pass"):
                        line = "auth-user-pass " + getAddonPathWrapper(vpn_provider + "/" + "pass.txt\n")

                # Update port numbers
                if line.startswith("remote "):
                    port = ""
                    for newline in lines:
                        if "proto " in newline:
                            if "tcp" in newline and not portTCP == "": port = portTCP
                            if "udp" in newline and not portUDP == "": port = portUDP
                    if not port == "":
                        tokens = line.split()
                        line = "remote " + tokens[1] + " " + port + "\n"

                # Update user cert and key                
                if usesUserKeys(vpn_provider):
                    if line.startswith("cert "):
                        line = "cert " + getUserDataPathWrapper(vpn_provider + "/" + getCertName(vpn_provider, name) + "\n")
                    if line.startswith("key "):
                        line = "key " + getUserDataPathWrapper(vpn_provider + "/" + getKeyName(vpn_provider, name) + "\n")
                
                # For user defined profile we need to replace any path tags with the addon dir path
                if isUserDefined(vpn_provider):
                    line = line.replace("#PATH", getAddonPathWrapper(vpn_provider))
                
                # Set the logging level
                if line.startswith("verb "):
                    line = "verb " + verb_value + "\n"
    
                f.write(line)
            f.close()
        except:
            errorTrace("vpnproviders.py", "Failed to update ovpn file")
            return False

    # Flag that the files have been generated            
    writeGeneratedFile(vpn_provider)
            
    return True    


def copyUserDefinedFiles():    
    # Copy everything in the user directory to the addon directory
    infoTrace("vpnproviders.py", "Copying user defined files from userdata directory")
    source_path = getUserDataPath((user_def_str)+"/")
    dest_path = getAddonPath(True, user_def_str + "/")
    # Get the list of connection profiles and another list of strings to abuse for the selection screen    
    try:
        files = getUserDataList(user_def_str, "*")
        if len(files) == 0:
            errorTrace("vpnproviders.py", "No User Defined files available to copy from " + source_path)
            return False
        for file in files:
            name = file[file.rfind(getSeparator())+1:]
            dest_file = dest_path + getSeparator() + name
            xbmcvfs.copy(file, dest_file)
        return True
    except:
        errorTrace("vpnproviders.py", "Error copying files from " + source_path + " to " + dest_path)
        return False


def writeGeneratedFile(vpn_provider):
    # Write a file to indicate successful generation of the ovpn files
    ovpn_file = open(getAddonPath(True, vpn_provider + "/GENERATED.txt"), 'w')
    ovpn_file.close()