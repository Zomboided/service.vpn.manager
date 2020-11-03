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
#    Code fragments specific to individual VPN providers.

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
import json
#FIXME PYTHON3
try:
    from urllib2 import urlopen as urlopen
    from urllib2 import Request as Request
    from urllib2 import HTTPError as HTTPError
except:
    from urllib.request import Request as Request
    from urllib.request import urlopen as urlopen
    from urllib.error import HTTPError as HTTPError
import time
from libs.utility import ifHTTPTrace, ifJSONTrace, debugTrace, infoTrace, errorTrace, ifDebug, newPrint, getID, now
from libs.vpnplatform import getAddonPath, getPlatform, platforms
from libs.access import setVPNRequestedServer, getVPNRequestedServer, resetTokens, setTokens, getTokens, setVPNURL, getVPNURL


REQUEST_HEADERS = {
    "x-shellfirevpn-client-os": "kodi",
    "x-shellfirevpn-client-arch": "zomboided",
    "x-shellfirevpn-client-version": "0.1"
}

REQUEST_URL = "https://www.shellfire.de/webservice/json.php"

SHELLFIRE_LOCATIONS = "COUNTRIES.txt"

ACCOUNT_TYPES = ["Free", "Premium", "PremiumPlus"]

UPGRADE_START = "[I]  "
UPGRADE_END = "[/I]"

SERVER_START = "  "
SERVER_END = ""

TITLE_START = "[B]"
TITLE_END = "[/B]"

TIME_WARN = 10


def getAddonPathWrapper(name):
    # Return the fully qualified add-on path and file name
    if getPlatform() == platforms.WINDOWS:
        return getAddonPath(True, name).replace("\\", "\\\\")
    else:
        return getAddonPath(True, name)


def getAccountType():
    # This returns the account type that was selected
    addon = xbmcaddon.Addon(getID())
    service = addon.getSetting("vpn_locations_list")
    type, id = service.split(";")
    return type
    
    
def getAccountID():
    # This returns the ID of the account that was selected
    addon = xbmcaddon.Addon(getID())
    service = addon.getSetting("vpn_locations_list")
    type, id = service.split(";")
    return id
    
    
def authenticateLogin(vpn_provider, userid, password):
    # Authenticate to get token
    resetTokens()
    rc, api_data = sendAPI("?action=login", "Authenticating with VPN", '{"email":"' + userid + '", "password":"' + password + '"}', True)
    if not rc: return None
        
    # Return the token to use for this user on future API calls
    return api_data["data"]["token"]
    
    
def getServices():
    # Get the list of services
    rc, api_data = sendAPI("?action=getAllVpnDetails", "Retrieving list of services", "", True)
    if not rc: return None
  
    # Extract and return the list of service levels the user is entitled to
    try:
        services = []
        service_list = ""
        for item in api_data["data"]:
            services.append(item["eAccountType"] +";" + str(item["iVpnId"]))
            service_list = service_list + item["eAccountType"] + ", (" + str(item["iVpnId"]) + ") "
        debugTrace("Found services " + service_list)
        return services
    except Exception as e:
        errorTrace("alternativeShellfire.py", "Couldn't parse the data that came back when listing the serice levels")
        errorTrace("alternativeShellfire.py", str(e))
        return None

        
def authenticateShellfire(vpn_provider, userid, password):
    # Authenticate with the API and store the tokens returned

    # If the same credentials have been used before, don't bother authenticating
    _,_,_, creds = getTokens()
    if creds == vpn_provider + userid + password: 
        debugTrace("Previous authentication was good")
        return True
    
    # Get the authentication token to use on future calls
    resetTokens()
    rc, api_data = sendAPI("?action=login", "Authenticating with VPN", '{"email":"' + userid + '", "password":"' + password + '"}', True)
    if not rc: return False
        
    # Extract the auth token and store it
    auth_token = api_data["data"]["token"]
    if not auth_token == None: 
        setTokens(auth_token, "", vpn_provider + userid + password)
        return True

    return False


def getShellfirePreFetch(vpn_provider):
    # Fetch and store location info
    filename = getAddonPath(True, vpn_provider + "/" + SHELLFIRE_LOCATIONS)
    if xbmcvfs.exists(filename):
        try:
            st = xbmcvfs.Stat(filename)
            create_time = int(st.st_ctime())
            t = now()
            # Fetch again if this is more than a day old otherwise use what there is
            if create_time + 86400 < t:
                debugTrace("Create time of " + filename + " is " + str(create_time) + " time now is " + str(t) + ", fetching location data again")
            else:
                debugTrace("Create time of " + filename + " is " + str(create_time) + " time now is " + str(t) + ", using existing data")
                # Less than a day old, so using the existing file
                return True
        except Exception as e:
            errorTrace("alternativeShellfire.py", "List of countries exist but couldn't get the time stamp for " + filename)
            errorTrace("alternativeShellfire.py", str(e))
            return False

    # Download the list of locations
    error = True
    try:
        response = ""
        api_data = ""
        rest_url = "https://www.shellfire.de/webservice/serverlist.php"
        
        if ifHTTPTrace(): infoTrace("alternativeShellfire.py", "Downloading list of locations using " + rest_url)
        else: debugTrace("Downloading list of locations")
        
        # This is not a JSON call, a header and servers are returned in a ; separated list
        req = Request(rest_url, "", REQUEST_HEADERS)
        t_before = now()
        response = urlopen(req)
        api_data = response.read()
        t_after = now()    
        response.close()

        if ifJSONTrace(): infoTrace("alternativeShellfire.py", "Text received is \n" + api_data)
        if t_after - t_before > TIME_WARN: infoTrace("alternativeShellfire.py", "Retrieving list of locations took " + str(t_after - t_before) + " seconds")
        
    except HTTPError as e:
        errorTrace("alternativeShellfire.py", "Couldn't retrieve the list of locations")
        errorTrace("alternativeShellfire.py", "API call was " + rest_url)
        if not api_data == "": errorTrace("alternativeShellfire.py", "Data returned was \n" + api_data)
        errorTrace("alternativeShellfire.py", "Response was " + str(e.code) + " " + e.reason)
        errorTrace("alternativeShellfire.py", e.read())
        return False
    except Exception as e:
        errorTrace("alternativeShellfire.py", "Couldn't retrieve the list of locations")
        errorTrace("alternativeShellfire.py", "API call was " + rest_url)
        if not api_data == "": errorTrace("alternativeShellfire.py", "Data returned was \n" + api_data)
        errorTrace("alternativeShellfire.py", "Response was " + str(type(e)) + " " + str(e))
        return False
            
    # The first line has the headers, so find the position of the information that's interesting
    api_table = api_data.split("\n") 
    headers = api_table[0].split(";")
    id_pos = headers.index("iVpnServerId")
    country_pos = headers.index("Country")
    city_pos = headers.index("sCity")
    host_pos = headers.index("sHost")
    type_pos = headers.index("eServerType")    
    debugTrace("Header decoded.  ID is " + str(id_pos) + ", Country is " + str(country_pos) + ", City is " + str(city_pos) + ", Host is " + str(host_pos) + ", Type is " + str(type_pos))
    api_table[0] = ""
    
    try:
        line = ""
        cleaned_data = []
        debugTrace("Parsing the text and extracting the country, server and type")
        for line in api_table:       
            server_data = line.split(";")
            # Avoid parsing empty lines, or lines where there's not enough data
            if len(server_data) > 5:
                cleaned_data.append(server_data[country_pos] + " - " + server_data[city_pos] + " (S" + server_data[id_pos] + ")," + server_data[host_pos] + "," + server_data[type_pos] + "," + server_data[id_pos] + "\n")
    except Exception as e:
        errorTrace("alternativeShellfire`.py", "Couldn't parse the list of locations for " + vpn_provider)
        if not server_data == "": errorTrace("alternativeShellfire.py", "Processing line " + line)
        errorTrace("alternativeShellfire.py", str(e))
        return False
        
    # Sort the locations alphabetically
    cleaned_data.sort()    
        
    try:
        line = ""
        debugTrace("Parsing the text and writing the list of locations")
        output = open(filename, 'w')
        # Parse the data and create list containing the stuff we care about
        for line in cleaned_data:       
            output.write(line)
        output.close()
        return True
    except Exception as e:
        errorTrace("alternativeShellfire`.py", "Couldn't write the list of locations for " + vpn_provider + " to " + filename)
        if not server_data == "": errorTrace("alternativeShellfire.py", "Processing server " + line)
        errorTrace("alternativeShellfire.py", str(e))

    # Delete the location file if the was a problem creating it.  This will force a download next time through
    try:
        if xbmcvfs.exists(filename): 
            errorTrace("alternativeShellfire.py", "Deleting location file " + filename + " to clean up after previous error")
            xbmcvfs.delete(filename)
    except Exception as e:
        errorTrace("alternativeShellfire.py", "Couldn't delete the location file " + filename)
        errorTrace("alternativeShellfire.py", str(e))
    return False
        
    
def getShellfireLocationsCommon(vpn_provider, exclude_used, friendly, servers):
    # Return a list of all of the locations
    addon = xbmcaddon.Addon(getID())
    # Get the list of used, validated location file names
    used = []
    if exclude_used:
        # Adjust the 11 below to change conn_max
        for i in range(1, 11):
            s = addon.getSetting(str(i) + "_vpn_validated_friendly")
            if not s == "" : used.append(s)

    filename = getAddonPath(True, vpn_provider + "/" + SHELLFIRE_LOCATIONS)
    # If the list of locations doesn't exist (this can happen after a reinstall)
    # then go and do the pre-fetch first.  Otherwise this shouldn't be necessary
    try:
        if not xbmcvfs.exists(filename):
            getShellfirePreFetch(vpn_provider)
    except Exception as e:
        errorTrace("alternativeShellfire.py", "Couldn't download the list of locations for " + vpn_provider + " from " + filename)
        errorTrace("alternativeShellfire.py", str(e))
        return [] 

    try:
        service = ACCOUNT_TYPES.index(getAccountType())
    except Exception as e:
        errorTrace("alternativeShellfire.py", "Don't have an account for " + vpn_provider)
        errorTrace("alternativeShellfire.py", str(e))
        return []
        
    try:
            
        # Read the locations from the file and list by account type
        locations_file = open(filename, 'r')
        locations = locations_file.readlines()
        locations_file.close()
        return_locations = []
        
        # List the free servers
        return_locations.append(TITLE_START + "Free Locations" + TITLE_END)
        for l in locations:
            country, server, type, server_id = l.split(",")
            server_id = server_id.strip(" \n")    
            if type == ACCOUNT_TYPES[0]:
                if not exclude_used or not country in used:
                    if friendly:
                        return_locations.append(SERVER_START + country + SERVER_END)
                    elif servers:
                        return_locations.append(SERVER_START + server + SERVER_END)
                    else:
                        return_locations.append(type + getShellfireLocationName(vpn_provider, country))

        # List the paid servers
        return_locations.append(TITLE_START + "Paid Locations" + TITLE_END)
        for l in locations:
            country, server, type, server_id = l.split(",")
            server_id = server_id.strip(" \n")
            if not type == ACCOUNT_TYPES[0]:
                if ACCOUNT_TYPES.index(type) > service:
                    start = UPGRADE_START
                    end = UPGRADE_END
                else:
                    start = SERVER_START
                    end = SERVER_END
                if not exclude_used or not country in used:
                    if friendly:
                        return_locations.append(start + country + end)
                    elif servers:
                        return_locations.append(start + server + end)
                    else:
                        return_locations.append(type + getShellfireLocationName(vpn_provider, country))

        return return_locations    
    except Exception as e:
        errorTrace("alternativeShellfire.py", "Couldn't read the list of locations for " + vpn_provider + " from " + filename)
        errorTrace("alternativeShellfire.py", str(e))
        return []
        
    return []
    

def getShellfireFriendlyLocations(vpn_provider, exclude_used):
    # Return the list of friendly location names
    return getShellfireLocationsCommon(vpn_provider, exclude_used, True, False)


def getShellfireLocations(vpn_provider, exclude_used):
    # Return the list of ovpn file names
    return getShellfireLocationsCommon(vpn_provider, exclude_used, False, False)


def getShellfireLocationName(vpn_provider, location):
    # Return the ovpn file name
    return getAddonPath(True, vpn_provider + "/" + location + ".ovpn")
    
    
def getShellfireLocation(vpn_provider, location, server_count, just_name):
    # Return the friendly and .ovpn name
    addon = xbmcaddon.Addon(getID())
    # Just return if this is a title that's been passed in
    if location.startswith(TITLE_START): return "", "", "Select a location or server", True
    # Remove all of the tagging
    # There's some escaping of the UPGRADE_END characters when passed in via the add-on menu
    # This is why the command below searches for the end of the upgrade and strips it
    location = location.replace(UPGRADE_START, "")
    if "I]" in location: location = location[:(location.index("I]")-2)]
    location = location.strip(" ")
    
    filename = getAddonPath(True, vpn_provider + "/" + SHELLFIRE_LOCATIONS)
    try:
        if not xbmcvfs.exists(filename):
            getShellfirePreFetch(vpn_provider)
    except Exception as e:
        errorTrace("alternativeShellfire.py", "Couldn't download the list of locations for " + vpn_provider + " from " + filename)
        errorTrace("alternativeShellfire.py", str(e))
        return "", "", "", False
           
    try:
        # Read the locations from the file and list by account type
        locations_file = open(filename, 'r')
        locations = locations_file.readlines()
        locations_file.close()
        for l in locations:
            if location in l:
                country, server, type, server_id = l.split(",")
                server_id = server_id.strip(" \n")
                break
        # Return an upgrade message if this server is not available to the user
        if ACCOUNT_TYPES.index(type) > ACCOUNT_TYPES.index(getAccountType()):
            _, message = getShellfireMessages(vpn_provider, 0, "")
            if message == "": message = "Get access to servers in over 30 countries with unlimited speed at shellfire.net/kodi"
            return "", "", "Upgrade to use this [B]" + type + "[/B] location.\n" + message, False
        
        # Generate the file name from the location
        location_filename = getShellfireLocationName(vpn_provider, country)
        
        if just_name: return location, location_filename, "", False
        
    except Exception as e:
        errorTrace("alternativeShellfire.py", "Couldn't read the list of locations for " + vpn_provider + " from " + filename)
        errorTrace("alternativeShellfire.py", str(e))
        return "", "", "", False
        
    # Set the selected server for the VPN being used
    try:
        setShellfireServer(getAccountID(), server_id)
        
        # Set the protocol.  If it's "UDP and TCP", choose UDP
        proto = addon.getSetting("vpn_protocol")
        if "UDP" in proto: proto = "UDP"
        if not setShellfireProtocol(getAccountID(), proto):
           raise Exception("Couldn't set the protocol") 
        
        # Get the parameters associated with this server and put them in a file
        if not getShellfireOvpn(getAccountID(), vpn_provider, country):
            raise Exception("Couldn't create an OVPN file") 
        
        # Get the certs associated with this server and put them in a file
        if not getShellfireCerts(getAccountID(), vpn_provider, country):
            raise Exception("Couldn't create the certificates") 

        return country, location_filename, "", False
    except Exception as e:
        errorTrace("alternativeShellfire.py", "Couldn't read the list of locations for " + vpn_provider + " from " + filename)
        errorTrace("alternativeShellfire.py", str(e))
        return "", "", "", False

        
def getShellfireServers(vpn_provider, exclude_used):
    # Return a list of all of the server files
    return getShellfireLocationsCommon(vpn_provider, exclude_used, False, False)

    
def getShellfireFriendlyServers(vpn_provider, exclude_used):
    # Return a list of all of the servers
    return getShellfireLocationsCommon(vpn_provider, exclude_used, False, True)


def getShellfireServer(vpn_provider, server, server_count, just_name):
    # Return the server and ovpn name
    # For Shellfire this is just returning the location name rather than the server URL
    return getShellfireLocation(vpn_provider, server, server_count, just_name)
    

def setShellfireServer(product_id, server_id):
    # Set the server for the product for active ID
    rc, api_data = sendAPI("?action=setServerTo", "Setting server", '{"productId": "' + product_id + '", "serverId": ' + server_id + '}', True)
    return rc

    
def setShellfireProtocol(product_id, protocol):
    # Set the protocol for the product for active ID
    rc, api_data = sendAPI("?action=setProtocol", "Setting protocol", '{"productId": "' + product_id + '", "proto": "' + protocol + '"}', True)
    return rc
    
    
def getShellfireOvpn(product_id, vpn_provider, country):
    # Retrieve the ovpn parameters and make them into an ovpn file
    rc, api_data = sendAPI("?action=getOpenVpnParams", "Retrieving openvpn params", '{"productId": "' + product_id + '"}', True)
    if not rc: return False
    
    # Parse the parameters and override some of them
    params = api_data["data"]["params"].split("--")
    filename = getAddonPath(True, vpn_provider + "/" + country + ".ovpn")
    output = open(filename, 'w')
    country_cert = "sf" + getAccountID()
    for p in params:
        p = p.strip(" \n")
        if p.startswith("service "): p = ""
        if p.startswith("ca "): p = "ca " + getAddonPathWrapper(vpn_provider + "/ca.crt")
        if p.startswith("cert "): p = "cert " + getAddonPathWrapper(vpn_provider + "/" + country_cert + ".crt")
        if p.startswith("key "): p = "key " + getAddonPathWrapper(vpn_provider + "/" + country_cert + ".key")
        if not p == "": output.write(p + "\n")
    
    output.close()
    
    return True
    
    
def getShellfireCerts(product_id, vpn_provider, country):

    # If the certs already exist, then just return
    # This is assuming that all of the certs remain the same, and are good for all connections for an account
    account_id = getAccountID()
    ca_name = getAddonPath(True, vpn_provider + "/" + "ca.crt")
    cert_name = getAddonPath(True, vpn_provider + "/" + "sf" + account_id + ".crt")
    key_name = getAddonPath(True, vpn_provider + "/" + "sf" + account_id + ".key")
    if xbmcvfs.exists(ca_name) and xbmcvfs.exists(cert_name) and xbmcvfs.exists(key_name): return True
    
    # Get the set of certificates that ar needed to connect
    rc, api_data = sendAPI("?action=getCertificates", "Retrieving certificates", '{"productId": "' + product_id + '"}', True)
    if not rc: return False
    
    # Write all of the certs to a file
    for item in api_data["data"]:
        cert_name = item["name"]
        if not writeCert(vpn_provider, cert_name, item["content"]): return False
    
    return True
    

def writeCert(vpn_provider, cert_name, content):
    # Write out the certificate represented by the content
    filename = getAddonPath(True, vpn_provider + "/" + cert_name)
    try:
        line = ""
        debugTrace("Writing certificate " + cert_name)
        output = open(filename, 'w')
        # Output the content line by line
        for line in content:       
            output.write(line)
        output.close()
        return True
    except Exception as e:
        errorTrace("alternativeShellfire`.py", "Couldn't write certificate " + filename)
        errorTrace("alternativeShellfire.py", str(e))
        return False

    
def getShellfireProfiles(vpn_provider):
    # Return selectable profiles, with alias to store and message
    # Get the list of services that are available to the user
    services = getServices()
    if services == None: return [], [], ""
    services.sort()
    display_userid = False
    for t in ACCOUNT_TYPES:
        count = 0
        for s in services:
            if s.startswith(t):
                count = count + 1
        if count > 1: display_userid = True
    
    # Create a list of those services
    i = 0
    userids = []
    for s in services:
        service, id = s.split(";")
        id = id.strip(" \n")
        userids.append(s)
        if display_userid:
            services[i] = "sf" + id + " (" + service + ")"
        else:
            services[i] = service
        i += 1
    
    return services, userids, "Select a VPN to use"    
        
    
def getShellfireMessages(vpn_provider, last_time, last_id):
    # Return any message ID and message available from the provider
    
    # Never return a message for a paid account unless a last_time of 0 is being used to force it
    if getAccountType() > 0 and not last_time == 0: return "", ""
    
    # Fetch any available deal
    rc, api_data = sendAPI("?action=getAvailablePricingDeal", "Retrieving messages", "", False)
    # Adding 'Success' to the end of this line will return a test message
    # Check the call worked and that it was successful.  If there's no message, a bad response is returned
    if not rc: return "", ""
    if not api_data["status"] == "success": return "", ""

    try:
        # Extract and format the message
        id = api_data["data"]["pricingDealId"]
        message = api_data["data"]["name"] + " - " + api_data["data"]["description"] + " - Only available until "
        ts = int(api_data["data"]["validUntil"])
        message = message + time.strftime("%b %d", time.gmtime(ts))
        message = message + " - " + api_data["data"]["url"]
        
        # Don't return a message if the same message was displayed < 1 week ago 
        if (not last_time == 0) and (last_time + 604800 > now()) and last_id == id:
            return "", ""
            
    except Exception as e:
        errorTrace("alternativeShellfire.py", "Couldn't format message returned")
        errorTrace("alternativeShellfire.py", "JSON received is \n" + json.dumps(api_data, indent=4))
        return "", ""
    
    return id, message
    
    
def checkForShellfireUpdates(vpn_provider):
    # See if the current stored tokens have changed
    addon = xbmcaddon.Addon(getID())
    current = addon.getSetting("vpn_locations_list")
    # If nothing has been selected/validated, then it doesn't matter if there's updates or not
    if current == "": return False
    # Likewise, if nothing is connected, then it doesn't matter yet
    if addon.getSetting("1_vpn_validated") == "": return False
    debugTrace("Checking for updates for " + current)
    # Get the list of services and see if the current ID is still the same
    services = getServices()
    if services == None: return False
    for s in services:
        # Look for the current service/id. If it's found nothing has been updated
        if s == current: return False
    # If we didn't find the service/id, then it's changed, so there are updates
    return True
    

def refreshFromShellfire(vpn_provider):
    # Force a refresh of the data from the VPN provider
    # Nothing to do for this provider, the caller will reset the validated connections
    return True


def regenerateShellfire(vpn_provider):
    # Regenerate any files required to connect
    # Nothing to do for Shellfire as it'll get what it needs during connection
    return True


def resetShellfire(vpn_provider):
    # Clear up any provider specific settings after deleting all files
    return True


def getShellfireUserPass(vpn_provider):
    # Use the user ID and password entered into the GUI
    addon = xbmcaddon.Addon(getID())
    return addon.getSetting("vpn_username"), addon.getSetting("vpn_password")
    
    
def sendAPI(command, command_text, api_data, check_response):
    # Common routine to send an API command
    try:
        response = ""
        rc = True
        rest_url = REQUEST_URL + command
        
        auth_token,_,_,_ = getTokens()
        # Login again if the token is blank and the command is not login anyway
        if auth_token == "" and not "=login" in command:
            debugTrace("Logging in again because auth token not valid")
            addon = xbmcaddon.Addon(getID())
            rc = authenticateShellfire(addon.getSetting("vpn_provider"), addon.getSetting("vpn_username"), addon.getSetting("vpn_password"))
            auth_token,_,_,_ = getTokens()
            if auth_token == "" or not rc:
                raise Exception(command_text + " was not authorized")
        
        if ifHTTPTrace(): infoTrace("alternativeShellfire.py", command_text + " " + rest_url)     
        else: debugTrace(command_text)
        
        req = Request(rest_url, api_data, REQUEST_HEADERS)
        if not auth_token == "": req.add_header("x-authorization-token", auth_token)
        t_before = now()
        response = urlopen(req)
        api_data = json.load(response)   
        t_after = now()    
        response.close()

        # Trace if the command took a long time
        if ifJSONTrace(): infoTrace("alternativeShellfire.py", "JSON received is \n" + json.dumps(api_data, indent=4))
        if t_after - t_before > TIME_WARN: infoTrace("alternativeShellfire.py", command_text + " took " + str(t_after - t_before) + " seconds")
        
        # Check the response and fail if it's bad
        if check_response:
            if not api_data["status"] == "success":
                raise Exception(command_text + " returned bad response, " + api_data["status"])
        
    except HTTPError as e:
        errorTrace("alternativeShellfire.py", command_text + " failed")
        errorTrace("alternativeShellfire.py", "API call was " + rest_url)
        if not api_data == "": errorTrace("alternativeShellfire.py", "Data returned was \n" + json.dumps(api_data, indent=4))
        errorTrace("alternativeShellfire.py", "Response was " + str(e.code) + " " + e.reason)
        errorTrace("alternativeShellfire.py", e.read())
        rc = False
    except Exception as e:
        errorTrace("alternativeShellfire.py", command_text + " failed")
        errorTrace("alternativeShellfire.py", "API call was " + rest_url)
        if not api_data == "": errorTrace("alternativeShellfire.py", "Data returned was \n" + json.dumps(api_data, indent=4))
        errorTrace("alternativeShellfire.py", "Response was " + str(type(e)) + " " + str(e))
        rc = False
    
    return rc, api_data


def postConnectShellfire(vpn_provider):
    # Post connect, nothing special to do for Shellfire
    return

