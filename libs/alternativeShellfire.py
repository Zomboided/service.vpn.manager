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
import urllib2
import time
from libs.utility import ifHTTPTrace, ifJSONTrace, debugTrace, infoTrace, errorTrace, ifDebug, newPrint, getID, now
from libs.platform import getAddonPath
from libs.access import setVPNRequestedServer, getVPNRequestedServer, resetTokens, setTokens, getTokens


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


def getHighestService():
    _,services,_,_ = getTokens()
    highest = ACCOUNT_TYPES[0]
    for t in ACCOUNT_TYPES:
        if (t + " ") in services:
            highest = t
    return highest
    
    
def authenticateLogin(vpn_provider, userid, password):
    # Authenticate to get token
    try: 
        response = ""
        api_data = ""
        rest_url = REQUEST_URL + "?action=login"
        rest_data = '{"email":"' + userid + '", "password":"' + password + '"}'

        if ifHTTPTrace(): infoTrace("alternativeShellfire.py", "Authenticating with VPN using " + rest_url + ", " + rest_data)     
        else: debugTrace("Authenticating with VPN for user " + userid)

        req = urllib2.Request(rest_url, rest_data, REQUEST_HEADERS)
        t_before = now()
        response = urllib2.urlopen(req)
        api_data = json.load(response)
        t_after = now()
        response.close()

        if ifJSONTrace(): infoTrace("alternativeShellfire.py", "JSON received is \n" + json.dumps(api_data, indent=4))
        if t_after - t_before > TIME_WARN: infoTrace("alternativeShellfire.py", "Authenticating with VPN for " + userid + " took " + str(t_after - t_before) + " seconds")

        if not api_data["status"] == "success":
            raise Exception("Bad response authenticating with VPN, " + api_data["status"] + " check user ID and password")
        
        # Return the token to use for this user on future API calls
        return api_data["data"]["token"]

    except urllib2.HTTPError as e:
        errorTrace("alternativeShellfire.py", "Couldn't authenticate with " + vpn_provider)
        errorTrace("alternativeShellfire.py", "API call was " + rest_url + ", " + rest_data[:rest_data.index("password")+10] + "********}")
        if not api_data == "": errorTrace("alternativeShellfire.py", "Data returned was \n" + json.dumps(api_data, indent=4))
        errorTrace("alternativeShellfire.py", "Response was " + str(e.code) + " " + e.reason)
        errorTrace("alternativeShellfire.py", e.read())
    except Exception as e:
        errorTrace("alternativeShellfire.py", "Couldn't authenticate with " + vpn_provider)
        errorTrace("alternativeShellfire.py", "API call was " + rest_url + ", " + rest_data[:rest_data.index("password")+10] + "********}")
        if not api_data == "": errorTrace("alternativeShellfire.py", "Data returned was \n" + json.dumps(api_data, indent=4))
        errorTrace("alternativeShellfire.py", "Response was " + str(type(e)) + " " + str(e))

    return None
    
    
def authenticateGetServices(auth_token):
    # Get the list of services  
    try:
        response = ""
        api_data = ""
        rest_url = REQUEST_URL + "?action=getAllVpnDetails"
        
        if ifHTTPTrace(): infoTrace("alternativeShellfire.py", "Retrieving list of services " + rest_url)     
        else: debugTrace("Retrieving list of services")
        
        req = urllib2.Request(rest_url, "", REQUEST_HEADERS)
        req.add_header("x-authorization-token", auth_token)
        t_before = now()
        response = urllib2.urlopen(req)
        api_data = json.load(response)   
        t_after = now()    
        response.close()

        if ifJSONTrace(): infoTrace("alternativeShellfire.py", "JSON received is \n" + json.dumps(api_data, indent=4))
        if t_after - t_before > TIME_WARN: infoTrace("alternativeShellfire.py", "Retrieving list of services took " + str(t_after - t_before) + " seconds")
        
        if not api_data["status"] == "success":
            raise Exception("Bad response getting services from VPN provider, " + api_data["status"])
        
        # Extract and return the list of service levels the user is entitled to
        services = ""
        for item in api_data["data"]:
            services = services + item["eAccountType"] + " "
        debugTrace("User has " + services + "active")
        # <FIXME>
        return "Free Premium "
        return services    
    
    except urllib2.HTTPError as e:
        errorTrace("alternativeShellfire.py", "Couldn't retrieve the list of services")
        errorTrace("alternativeShellfire.py", "API call was " + rest_url)
        if not api_data == "": errorTrace("alternativeShellfire.py", "Data returned was \n" + json.dumps(api_data, indent=4))
        errorTrace("alternativeShellfire.py", "Response was " + str(e.code) + " " + e.reason)
        errorTrace("alternativeShellfire.py", e.read())
    except Exception as e:
        errorTrace("alternativeShellfire.py", "Couldn't retrieve the list of services")
        errorTrace("alternativeShellfire.py", "API call was " + rest_url)
        if not api_data == "": errorTrace("alternativeShellfire.py", "Data returned was \n" + json.dumps(api_data, indent=4))
        errorTrace("alternativeShellfire.py", "Response was " + str(type(e)) + " " + str(e))
    
    return None


def authenticateShellfire(vpn_provider, userid, password):
    # Authenticate with the API and store the tokens returned

    # If the same credentials have been used before, don't bother authenticating
    _,_,_, creds = getTokens()
    # FIXME REMOVE THIS AFTER TESTING
    if 1==0 and creds == vpn_provider + userid + password: 
        debugTrace("Previous authentication was good")
        return True
    
    # Get the authentication token to use on future calls
    auth_token = authenticateLogin(vpn_provider, userid, password)
    if not auth_token == None: 
        services = authenticateGetServices(auth_token)
        if not services == None:
            # Store all of the authentication info
            setTokens(auth_token, services, vpn_provider + userid + password)
            return True

    # Authentication or retrieval of services failed so clean up
    resetTokens()
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
                # <FIXME> Remove this after testing, this forces the list to always be downloaded
                # return True
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
        req = urllib2.Request(rest_url, "", REQUEST_HEADERS)
        t_before = now()
        response = urllib2.urlopen(req)
        api_data = response.read()
        t_after = now()    
        response.close()

        if ifJSONTrace(): infoTrace("alternativeShellfire.py", "Text received is \n" + api_data)
        if t_after - t_before > TIME_WARN: infoTrace("alternativeShellfire.py", "Retrieving list of locations took " + str(t_after - t_before) + " seconds")
        
    except urllib2.HTTPError as e:
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
    
    services = ACCOUNT_TYPES.index(getHighestService())
    
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
                if ACCOUNT_TYPES.index(type) > services:
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
    return getShellfireLocationsCommon(vpn_provider, exclude_used, True, False)


def getShellfireLocations(vpn_provider, exclude_used):
    return getShellfireLocationsCommon(vpn_provider, exclude_used, False, False)


def getShellfireLocationName(vpn_provider, location):
    # <FIXME> although this is probably right
    return getAddonPath(True, vpn_provider + "/" + location + ".ovpn")
    
    
def getShellfireLocation(vpn_provider, location, server_count):
    # Return the friendly and .ovpn name
    if location.startswith(TITLE_START): return "", "", "Select a location or server"
    # Remove all of the tagging
    location = location.strip(" ")
    location = location.replace(UPGRADE_START, "")
    location = location.replace(UPGRADE_END, "")
    
    try:
        # Read the locations from the file and list by account type
        filename = getAddonPath(True, vpn_provider + "/" + SHELLFIRE_LOCATIONS)
        locations_file = open(filename, 'r')
        locations = locations_file.readlines()
        locations_file.close()
        for l in locations:
            if location in l:
                country, server, type, server_id = l.split(",")
                server_id = server_id.strip(" \n")
                newPrint("Server >" + server_id + "<")
                break
        # Return an upgrade message if this server is not available to the user
        if ACCOUNT_TYPES.index(type) > ACCOUNT_TYPES.index(getHighestService()):
            _, message = getShellfireMessages(vpn_provider, 0)
            if message == "": message = "Get access to servers in over 30 countries with unlimited speed at shellfire.net/kodi"
            return "", "", "Upgrade to use this [B]" + type + "[/B] location.\n" + message
        
        # Generate the file name from the location
        location_file = getShellfireLocationName(vpn_provider, country)
        
        
        setShellfireServer(server_id, "510829")
        
        # FIXME
        # Generate the ovpn file here!
        
        
        return country, location_file, ""
        
    except Exception as e:
        errorTrace("alternativeShellfire.py", "Couldn't read the list of locations for " + vpn_provider + " from " + filename)
        errorTrace("alternativeShellfire.py", str(e))
        return "", "", ""
    

def getShellfireServers(vpn_provider, exclude_used):
    # Return a list of all of the server files
    return getShellfireLocationsCommon(vpn_provider, exclude_used, False, False)

    
def getShellfireFriendlyServers(vpn_provider, exclude_used):
    # Return a list of all of the servers
    return getShellfireLocationsCommon(vpn_provider, exclude_used, False, True)


def getShellfireServer(vpn_provider, server, server_count):
    # <FIXME> This is the same logic as location, but I think I should return the name.
    # If I have to return the server then I can just use the server param passed in
    return getShellfireLocation(vpn_provider, server, server_count)
    

def setShellfireServer(server_id, product_id):
    # Set the server for the product for active ID
    try:
        response = ""
        api_data = ""
        auth_token,_,_,_ = getTokens()
        rest_url = REQUEST_URL + "?action=setServerTo"
        rest_data = '{"serverId": "' + server_id + '", "productId": "' + product_id + '"}'
        
        if ifHTTPTrace(): infoTrace("alternativeShellfire.py", "Setting server " + rest_url + ", " + rest_data)     
        else: debugTrace("Setting server for server " + server_id)
        
        req = urllib2.Request(rest_url, "", REQUEST_HEADERS)
        req.add_header("x-authorization-token", auth_token)
        t_before = now()
        response = urllib2.urlopen(req)
        api_data = json.load(response)   
        t_after = now()    
        response.close()

        if ifJSONTrace(): infoTrace("alternativeShellfire.py", "JSON received is \n" + json.dumps(api_data, indent=4))
        if t_after - t_before > TIME_WARN: infoTrace("alternativeShellfire.py", "Setting server took " + str(t_after - t_before) + " seconds")
        
        # A success status won't be returned if there are no messages
        if not api_data["status"] == "success":
            return "", ""
            
    except urllib2.HTTPError as e:
        errorTrace("alternativeShellfire.py", "Couldn't set server")
        errorTrace("alternativeShellfire.py", "API call was " + rest_url)
        if not api_data == "": errorTrace("alternativeShellfire.py", "Data returned was \n" + json.dumps(api_data, indent=4))
        errorTrace("alternativeShellfire.py", "Response was " + str(e.code) + " " + e.reason)
        errorTrace("alternativeShellfire.py", e.read())
        return "", ""
    except Exception as e:
        errorTrace("alternativeShellfire.py", "Couldn't set server")
        errorTrace("alternativeShellfire.py", "API call was " + rest_url)
        if not api_data == "": errorTrace("alternativeShellfire.py", "Data returned was \n" + json.dumps(api_data, indent=4))
        errorTrace("alternativeShellfire.py", "Response was " + str(type(e)) + " " + str(e))
        return "", ""
    
    
def getShellfireProfiles(vpn_provider):
    # Return selectable profiles, with alias to store and message
    # <FIXME> List the accounts here, including the user ID
    return [], [], ""    
        
    
def getShellfireMessages(vpn_provider, last_time):
    # Return any message ID and message available from the provider
    try:
        response = ""
        api_data = ""
        auth_token,_,_,_ = getTokens()
        rest_url = REQUEST_URL + "?action=getAvailablePricingDealSuccess"
        # <FIXME> I can add 'Success' to the end of this for a test deal
        
        if ifHTTPTrace(): infoTrace("alternativeShellfire.py", "Retrieving messages " + rest_url)     
        else: debugTrace("Retrieving messages")
        
        req = urllib2.Request(rest_url, "", REQUEST_HEADERS)
        req.add_header("x-authorization-token", auth_token)
        t_before = now()
        response = urllib2.urlopen(req)
        api_data = json.load(response)   
        t_after = now()    
        response.close()

        if ifJSONTrace(): infoTrace("alternativeShellfire.py", "JSON received is \n" + json.dumps(api_data, indent=4))
        if t_after - t_before > TIME_WARN: infoTrace("alternativeShellfire.py", "Retrieving messages took " + str(t_after - t_before) + " seconds")
        
        # A success status won't be returned if there are no messages
        if not api_data["status"] == "success":
            return "", ""
    except urllib2.HTTPError as e:
        errorTrace("alternativeShellfire.py", "Couldn't retrieve messages")
        errorTrace("alternativeShellfire.py", "API call was " + rest_url)
        if not api_data == "": errorTrace("alternativeShellfire.py", "Data returned was \n" + json.dumps(api_data, indent=4))
        errorTrace("alternativeShellfire.py", "Response was " + str(e.code) + " " + e.reason)
        errorTrace("alternativeShellfire.py", e.read())
        return "", ""
    except Exception as e:
        errorTrace("alternativeShellfire.py", "Couldn't retrieve messages")
        errorTrace("alternativeShellfire.py", "API call was " + rest_url)
        if not api_data == "": errorTrace("alternativeShellfire.py", "Data returned was \n" + json.dumps(api_data, indent=4))
        errorTrace("alternativeShellfire.py", "Response was " + str(type(e)) + " " + str(e))
        return "", ""
    
    try:
        id = api_data["data"]["pricingDealId"]
        message = api_data["data"]["name"] + " - " + api_data["data"]["description"] + " - Only available until "
        ts = int(api_data["data"]["validUntil"])
        message = message + time.strftime("%b %d", time.gmtime(ts))
        message = message + " - " + api_data["data"]["url"]
    except Exception as e:
        errorTrace("alternativeShellfire.py", "Couldn't format message returned")
        errorTrace("alternativeShellfire.py", "JSON received is \n" + json.dumps(api_data, indent=4))
        return "", ""
    
    # Don't return a message for a paid account, or if we've returned it within the week
    # For callers that must always get the message back, return it if last_time is set to 0
    if (not last_time == 0) and (getHighestService() > 0 or last_time + 604800 > now()):
        return "", ""

    return id, message
    

def regenerateShellfire(vpn_provider):
    # <FIXME>
    return True


def resetShellfire(vpn_provider):
    # <FIXME>
    return True


def getShellfireUserPass(vpn_provider):
    # Use the user ID and password entered into the GUI
    # <FIXME> This might need reviewing depending on the data that comes back from the call to get the params
    addon = xbmcaddon.Addon(getID())
    return addon.getSetting("vpn_username"), addon.getSetting("vpn_password")
    


