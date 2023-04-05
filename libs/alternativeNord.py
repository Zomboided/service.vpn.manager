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
import urllib
#FIXME PYTHON3
try:
    from urllib import urlencode as urlencode
    from urllib2 import urlopen as urlopen
    from urllib2 import Request as Request
    from urllib2 import HTTPError as HTTPError
except:
    from urllib.parse import urlencode as urlencode
    from urllib.request import Request as Request
    from urllib.request import urlopen as urlopen
    from urllib.error import HTTPError as HTTPError
import time
from libs.utility import ifHTTPTrace, ifJSONTrace, debugTrace, infoTrace, errorTrace, ifDebug, newPrint, getID, now
from libs.vpnplatform import getAddonPath, getSystemdPath, copySystemdFiles, fakeSystemd
from libs.access import setVPNRequestedServer, getVPNRequestedServer, resetTokens, setTokens, getTokens, setVPNURL, getVPNURL, getVPNProfile

NORD_LOCATIONS = "COUNTRIES.txt"

TIME_WARN = 10


def authenticateNordVPN(vpn_provider, userid, password):
    # Authenticate with the API and store the tokens returned
    # Originally, the Nord API allowed the user to log in to get a token, but they've since moved to getting a 
    # token from a webpage, which can be input on the main screen.
    addon = xbmcaddon.Addon(getID())
    token = addon.getSetting("vpn_token")
    
    if token is None or token == "":
        # If not authenticated with a token, determine the token
        debugTrace("No token available, input one in the settings panel")
        return False
        
        # Actually this code doesn't work anymore since april 2023 but it's kept for ... who knows it will be needed again later.

        # If the same credentials have been used before, don't bother authenticating
        _,_,_, creds = getTokens()
        if creds == vpn_provider + userid + password:
            debugTrace("Previous authentication was good")
            return True

        response = ""
        download_url = "https://api.nordvpn.com/v1/users/tokens"
        download_data = (urlencode({'username': userid, 'password': password})).encode("utf-8")
        try:
            if ifHTTPTrace(): infoTrace("alternativeNord.py", "Authenticating with VPN using " + download_url + ", " + (download_data.decode("utf-8"))[:str(download_data).index("&password")+8] + "********")
            else: debugTrace("Authenticating with VPN for user " + userid)
            req = Request(download_url, download_data)
            t_before = now()
            response = urlopen(req, timeout=10)
            user_data = json.load(response)
            t_after = now()
            response.close()
            if ifJSONTrace(): infoTrace("alternativeNord.py", "JSON received is \n" + json.dumps(user_data, indent=4))
            if t_after - t_before > TIME_WARN: infoTrace("alternativeNord.py", "Authenticating with VPN for " + userid + " took " + str(t_after - t_before) + " seconds")
            setTokens(user_data["token"], user_data["renew_token"], None)
            setTokens(user_data["token"], user_data["renew_token"], vpn_provider + userid + password)
            return True
        except HTTPError as e:
            errorTrace("alternativeNord.py", "Couldn't authenticate with " + vpn_provider)
            errorTrace("alternativeNord.py", "API call was " + download_url + ", " + (download_data.decode("utf-8"))[:str(download_data).index("&password")+8] + "********")
            errorTrace("alternativeNord.py", "Response was " + str(e.code) + " " + e.reason)
            errorTrace("alternativeNord.py", e.read())
        except Exception as e:
            errorTrace("alternativeNord.py", "Couldn't authenticate with " + vpn_provider)
            errorTrace("alternativeNord.py", "API call was " + download_url + ", " + (download_data.decode("utf-8"))[:str(download_data).index("&password")+8] + "********")
            errorTrace("alternativeNord.py", "Response was " + str(type(e)) + " " + str(e))
        resetTokens()
        return False
    else:
        # The token is povided via the addon settings and we assume this is a correct token
        return True


def renewNordVPN(renew):
    # This should never be called as of April 2023
    errorTrace("alternativeNord.py", "Not expecting to renew the token")
    return False

    # Renew a user with the API and store the tokens returned
    response = ""
    download_url = "https://api.nordvpn.com/v1/users/tokens/renew"
    download_data = ("renewToken=" + renew).encode("utf-8")
    try:
        if ifHTTPTrace(): infoTrace("alternativeNord.py", "Renewing authentication using " + download_url + ", " + (download_data.decode("utf-8"))[:str(download_data).index("renewToken")+9] + "********")
        else: debugTrace("Renewing authentication")
        req = Request(download_url, download_data)
        t_before = now()
        response = urlopen(req, timeout=10)
        user_data = json.load(response)
        t_after = now()
        response.close()
        if ifJSONTrace(): infoTrace("alternativeNord.py", "JSON received is \n" + json.dumps(user_data, indent=4))
        if t_after - t_before > TIME_WARN: infoTrace("alternativeNord.py", "Renewing authentication took " + str(t_after - t_before) + " seconds")
        setTokens(user_data["token"], user_data["renew_token"], None)
        return True
    except HTTPError as e:
        errorTrace("alternativeNord.py", "Couldn't renew user token")
        errorTrace("alternativeNord.py", "API call was " + download_url + ", " + (download_data.decode("utf-8"))[:str(download_data).index("renewToken")+9] + "********")
        errorTrace("alternativeNord.py", "Response was " + str(e.code) + " " + e.reason)
        errorTrace("alternativeNord.py", e.read())
    except Exception as e:
        errorTrace("alternativeNord.py", "Couldn't renew user token")
        errorTrace("alternativeNord.py", "API call was " + download_url + ", " + (download_data.decode("utf-8"))[:str(download_data).index("renewToken")+9] + "********")
        errorTrace("alternativeNord.py", "Response was " + str(type(e)) + " " + str(e))
    resetTokens()
    return False


def getTokenNordVPN():
    # Return a token that can be used on API calls
    addon = xbmcaddon.Addon(getID())
    token = addon.getSetting("vpn_token") # token provided via api settings
    
    if token is None or token == "":
        # No token is provided via the api settings so must determine it via the login creedentials
        debugTrace("No token available, input one in the settings panel")
        return False

        # Actually this code doesn't work anymore since april 2023 but it's kept for ... who knows it will be needed again later.
        token, renew, expiry, _ = getTokens()

        # If the expiry time is passed, renew the token
        if (expiry.isdigit() and int(expiry) < now()):
            if renewNordVPN(renew):
                token, _, _, _ = getTokens()
                return token
            else:
                # Force an authenticate to happen
                token = ""

        # The authentication call is made during connection validation, which will validate everything and fetch
        # the tokens.  If a reboot happens and the tokens disappear, then we need to force an authenticate again
        if token == "":
            if authenticateNordVPN(addon.getSetting("vpn_provider_validated"), addon.getSetting("vpn_username_validated"), addon.getSetting("vpn_password_validated")):
                token, _, _, _ = getTokens()
                return token
            else:
                errorTrace("alternativeNord.py", "Couldn't authenticate or renew the user ID")
                resetTokens()
                raise RuntimeError("Couldn't get a user ID token")

        debugTrace("Using existing user ID token")

    return token


def getNordVPNUserPass(vpn_provider):
    # Download the opvn file
    download_url = "https://api.nordvpn.com/v1/users/services/credentials"
    try:
        if ifHTTPTrace(): infoTrace("alternativeNord.py", "Getting user credentials " + download_url)
        else: debugTrace("Getting user credentials")
        token = getTokenNordVPN()
        req = Request(download_url)
        req.add_header("Authorization", "token:" + token)
        t_before = now()
        response = urlopen(req, timeout=10)
        user_data = json.load(response)
        t_after = now()
        response.close()
        if ifJSONTrace(): infoTrace("alternativeNord.py", "JSON received is \n" + json.dumps(user_data, indent=4))
        if t_after - t_before > TIME_WARN: infoTrace("alternativeNord.py", "Getting user credentials took " + str(t_after - t_before) + " seconds")
        return user_data["username"], user_data["password"]
    except HTTPError as e:
        errorTrace("alternativeNord.py", "Couldn't get user credentials")
        errorTrace("alternativeNord.py", "API call was " + download_url)
        errorTrace("alternativeNord.py", "Response was " + str(e.code) + " " + e.reason)
        errorTrace("alternativeNord.py", e.read())
        return "", ""
    except Exception as e:
        errorTrace("alternativeNord.py", "Couldn't get user credentials")
        errorTrace("alternativeNord.py", "API call was " + download_url)
        errorTrace("alternativeNord.py", "Response was " + str(type(e)) + " " + str(e))
        return "", ""


def getNordVPNPreFetch(vpn_provider):
    # Fetch and store country info from the magical interwebz
    filename = getAddonPath(True, vpn_provider + "/" + NORD_LOCATIONS)
    if xbmcvfs.exists(filename):
        try:
            st = xbmcvfs.Stat(filename)
            create_time = int(st.st_ctime())
            t = now()
            # Fetch again if this is more than a day old otherwise use what there is
            if create_time + 86400 < t:
                debugTrace("Create time of " + filename + " is " + str(create_time) + " time now is " + str(t) + ", fetching country data again")
            else:
                debugTrace("Create time of " + filename + " is " + str(create_time) + " time now is " + str(t) + ", using existing data")
                return True
        except Exception as e:
            errorTrace("alternativeNord.py", "List of countries exist but couldn't get the time stamp for " + filename)
            errorTrace("alternativeNord.py", str(e))
            return False

    # Download the JSON object of countries
    response = ""
    download_url = ""
    error = True
    try:
        download_url = "https://api.nordvpn.com/v1/servers/countries"
        if ifHTTPTrace(): infoTrace("alternativeNord.py", "Downloading list of countries using " + download_url)
        else: debugTrace("Downloading list of countries")
        token = getTokenNordVPN()
        req = Request(download_url)
        req.add_header("Authorization", "token:" + token)
        t_before = now()
        response = urlopen(req, timeout=10)
        country_data = json.load(response)
        t_after = now()
        response.close()
        error = False
        if ifJSONTrace(): infoTrace("alternativeNord.py", "JSON received is \n" + json.dumps(country_data, indent=4))
        if t_after - t_before > TIME_WARN: infoTrace("alternativeNord.py", "Downloading list of countries took " + str(t_after - t_before) + " seconds")
    except HTTPError as e:
        errorTrace("alternativeNord.py", "Couldn't retrieve the list of countries for " + vpn_provider)
        errorTrace("alternativeNord.py", "API call was " + download_url)
        errorTrace("alternativeNord.py", "Response was " + str(e.code) + " " + e.reason)
        errorTrace("alternativeNord.py", e.read())
    except Exception as e:
        errorTrace("alternativeNord.py", "Couldn't retrieve the list of countries for " + vpn_provider)
        errorTrace("alternativeNord.py", "API call was " + download_url)
        errorTrace("alternativeNord.py", "Response was " + str(type(e)) + " " + str(e))

    if error:
        # Use the existing list of countries if there is one as it'll be pretty much up to date
        if xbmcvfs.exists(filename):
            infoTrace("alternativeNord.py", "Using existing list of countries")
            return True
        else:
            return False

    # Parse the JSON to write out the countries and ID
    try:
        debugTrace("Parsing the JSON and writing the list of countries")
        output = open(filename, 'w')
        for item in country_data:
            name = item["name"].replace(",","")
            output.write(name + "," + str(item["id"]) + "\n")
        output.close()
        return True
    except Exception as e:
        errorTrace("alternativeNord.py", "Couldn't write the list of countries for " + vpn_provider + " to " + filename)
        errorTrace("alternativeNord.py", str(e))

    # Delete the country file if the was a problem creating it.  This will force a download next time through
    try:
        if xbmcvfs.exists(filename):
            errorTrace("alternativeNord.py", "Deleting country file " + filename + " to clean up after previous error")
            xbmcvfs.delete(filename)
    except Exception as e:
        errorTrace("alternativeNord.py", "Couldn't delete the country file " + filename)
        errorTrace("alternativeNord.py", str(e))
    return False


def getNordVPNLocationsCommon(vpn_provider, exclude_used, friendly):
    # Return a list of all of the locations or location .ovpn files
    addon = xbmcaddon.Addon(getID())
    # Get the list of used, validated location file names
    used = []
    if exclude_used:
        # Adjust the 11 below to change conn_max
        for i in range(1, 11):
            s = addon.getSetting(str(i) + "_vpn_validated_friendly")
            if not s == "" : used.append(s)

    filename = getAddonPath(True, vpn_provider + "/" + NORD_LOCATIONS)
    # If the list of countries doesn't exist (this can happen after a reinstall)
    # then go and do the pre-fetch first.  Otherwise this shouldn't be necessary
    try:
        if not xbmcvfs.exists(filename):
            getNordVPNPreFetch(vpn_provider)
    except Exception as e:
        errorTrace("alternativeNord.py", "Couldn't download the list of countries for " + vpn_provider + " from " + filename)
        errorTrace("alternativeNord.py", str(e))
        return []

    # Read the locations file and generate the location file name, excluding any that are used
    try:

        locations_file = open(filename, 'r')
        locations = locations_file.readlines()
        locations_file.close()
        return_locations = []
        for l in locations:
            country, id = l.split(",")
            if not exclude_used or not country in used:
                if friendly:
                    return_locations.append(country)
                else:
                    return_locations.append(getNordVPNLocationName(vpn_provider, country))
        return return_locations
    except Exception as e:
        errorTrace("alternativeNord.py", "Couldn't read the list of countries for " + vpn_provider + " from " + filename)
        errorTrace("alternativeNord.py", str(e))
        return []


def getNordVPNLocations(vpn_provider, exclude_used):
    return getNordVPNLocationsCommon(vpn_provider, exclude_used, False)


def getNordVPNFriendlyLocations(vpn_provider, exclude_used):
    return getNordVPNLocationsCommon(vpn_provider, exclude_used, True)


def getNordVPNLocationName(vpn_provider, location):
    return getAddonPath(True, vpn_provider + "/" + location + ".ovpn")


def getNordVPNLocation(vpn_provider, location, server_count, just_name):
    # Return friendly name and .ovpn file name
    # Given the location, find the country ID of the servers
    addon = xbmcaddon.Addon(getID())

    filename = getAddonPath(True, vpn_provider + "/" + NORD_LOCATIONS)
    # If the list of countries doesn't exist (this can happen after a reinstall)
    # then go and do the pre-fetch first.  Otherwise this shouldn't be necessary
    try:
        if not xbmcvfs.exists(filename):
            getNordVPNPreFetch(vpn_provider)
    except Exception as e:
        errorTrace("alternativeNord.py", "Couldn't download the list of countries to get ID for " + vpn_provider + " from " + filename)
        errorTrace("alternativeNord.py", str(e))
        return "", "", "", False

    try:
        locations_file = open(filename, 'r')
        locations = locations_file.readlines()
        locations_file.close()
        id = ""
        for l in locations:
            country, id = l.split(",")
            id = id.strip(' \t\n\r')
            if location == country:
                break
        if id == "":
            errorTrace("alternativeNord.py", "Couldn't retrieve location " + location + " for " + vpn_provider + " from " + filename)
            return "", "", "", False
    except Exception as e:
        errorTrace("alternativeNord.py", "Couldn't read the list of countries to get ID for " + vpn_provider + " from " + filename)
        errorTrace("alternativeNord.py", str(e))
        return "", "", "", False

    # Generate the file name from the location
    location_filename = getNordVPNLocationName(vpn_provider, location)

    if just_name: return location, location_filename, "", False

    # Download the JSON object of servers
    response = ""
    download_url = ""
    error = True
    try:
        if "UDP" in addon.getSetting("vpn_protocol"): protocol = "udp"
        else: protocol = "tcp"
        download_url = "https://api.nordvpn.com/v1/servers/recommendations?filters[servers_technologies][identifier]=openvpn_" + protocol + "&filters[country_id]=" + id + "&filters[servers_groups][identifier]=legacy_standard"
        if ifHTTPTrace(): infoTrace("alternativeNord.py", "Downloading server info for " + location + " with ID " + id + " and protocol " + protocol + " using " + download_url)
        else: debugTrace("Downloading server info for " + location + " with ID " + id + " and protocol " + protocol)
        token = getTokenNordVPN()
        req = Request(download_url)
        req.add_header("Authorization", "token:" + token)
        t_before = now()
        response = urlopen(req, timeout=10)
        server_data = json.load(response)
        t_after = now()
        response.close()
        error = False
        if ifJSONTrace(): infoTrace("alternativeNord.py", "JSON received is \n" + json.dumps(server_data, indent=4))
        if t_after - t_before > TIME_WARN: infoTrace("alternativeNord.py", "Downloading server info for " + location + " with ID " + id + " and protocol " + protocol + " took " + str(t_after - t_before) + " seconds")
    except HTTPError as e:
        errorTrace("alternativeNord.py", "Couldn't retrieve the server info for " + vpn_provider + " location " + location + ", ID " + id)
        errorTrace("alternativeNord.py", "API call was " + download_url)
        errorTrace("alternativeNord.py", "Response was " + str(e.code) + " " + e.reason)
        errorTrace("alternativeNord.py", e.read())
    except Exception as e:
        errorTrace("alternativeNord.py", "Couldn't retrieve the server info for " + vpn_provider + " location " + location + ", ID " + id)
        errorTrace("alternativeNord.py", "API call was " + download_url)
        errorTrace("alternativeNord.py", "Response was " + str(type(e)) + " " + str(e))

    if error:
        # If there's an API connectivity issue but a location file exists then use that
        # Won't have the latest best location in it though
        if xbmcvfs.exists(location_filename):
            infoTrace("alternativeNord.py", "Using existing " + location + " file")
            return location, location_filename, "", False
        else:
            return "", "", "", False

    # First server is the best one, but if it didn't connect last time then skip it.  The last attempted server
    # will be cleared on a restart, or a successful connection.  If there are no more connections to try, then
    # it will try the first connection again.  However, if this is > 4th attempt to connect outside of the
    # validation then it'll always default to the best as it's likely there's a network rather than server problem
    last = getVPNRequestedServer()
    if not last == "" and server_count < 5:
        debugTrace("Server " + last + " didn't connect last time so will be skipping to the next server.")
        last_found = False
    else:
        last = ""
        last_found = True
    first_server = ""
    for item in server_data:
        name = item["name"]
        server = item["hostname"]
        status = item["status"]
        load = str(item["load"])
        #debugTrace("Next is " + name + ", " + server + ", " + status + ". Load is " + load)
        if status == "online":
            if first_server == "": first_server = server
            if last_found:
                debugTrace("Using " + name + ", " + server + ", online. Load is " + load)
                break
            if server == last: last_found = True
        server = ""
    if server == "": server = first_server
    setVPNRequestedServer(server)
    setVPNURL(server)

    # Fetch the ovpn file for the server
    if not server == "":
        if not getNordVPNOvpnFile(server, protocol, location_filename):
            if not xbmcvfs.exists(location_filename):
                return "", "", "", False
        return location, location_filename, "", False
    else:
        return "", "", "", False


def getNordVPNOvpnFile(server, protocol, target_file):
    # Download the opvn file
    download_url = "https://downloads.nordcdn.com/configs/files/ovpn_" + protocol + "/servers/" + server + "." + protocol + ".ovpn"
    try:
        if ifHTTPTrace(): infoTrace("alternativeNord.py", "Downloading ovpn for " + server + ", protocol " + protocol + " using " + download_url)
        else: debugTrace("Downloading ovpn for " + server + ", protocol " + protocol)
        token = getTokenNordVPN()
        req = Request(download_url)
        req.add_header("Authorization", "token:" + token)
        t_before = now()
        response = urlopen(req, timeout=10)
        lines = (response.read().decode('utf-8')).split("\n");
        t_after = now()
        response.close()
        if t_after - t_before > TIME_WARN: infoTrace("alternativeNord.py", "Downloading ovpn for " + server + ", protocol " + protocol + " took " + str(t_after - t_before) + " seconds")
    except HTTPError as e:
        errorTrace("alternativeNord.py", "Couldn't download the ovpn for server " + server + ", protocol " + protocol)
        errorTrace("alternativeNord.py", "API call was " + download_url)
        errorTrace("alternativeNord.py", "Response was " + str(e.code) + " " + e.reason)
        errorTrace("alternativeNord.py", e.read())
        return False
    except Exception as e:
        errorTrace("alternativeNord.py", "Couldn't download the ovpn for server " + server + ", protocol " + protocol)
        errorTrace("alternativeNord.py", "API call was " + download_url)
        errorTrace("alternativeNord.py", "Response was " + str(type(e)) + " " + str(e))
        return False

    try:
        debugTrace("Writing ovpn file to " + target_file)
        f = open(target_file, 'w')
        for line in lines:
            line = line.strip(' \t\n\r')
            f.write(line + "\n")
        f.close()
        return True
    except Exception as e:
        errorTrace("alternativeNord.py", "Couldn't write ovpn to " + target_file)
        errorTrace("alternativeNord.py", str(e))
        return False


def getNordVPNServers(vpn_provider, exclude_used):
    # Return a list of all of the server files
    # Not supported for this provider
    return []


def getNordVPNFriendlyServers(vpn_provider, exclude_used):
    # Return a list of all of the servers
    # Not supported for this provider
    return []


def getNordVPNServer(vpn_provider, server, server_count, just_name):
    # Return friendly name and .ovpn file name
    # Not supported for this provider
    return "", "", "", False


def getNordVPNMessages(vpn_provider, last_time, last_id):
    # Return any message ID and message available from the provider
    # Not supported for this provider
    return "", ""


def checkForNordVPNUpdates(vpn_provider):
    # See if the current stored tokens have changed
    # Nothing to do for this provider so report there are no updates
    return False


def refreshFromNordVPN(vpn_provider):
    # Force a refresh of the data from the VPN provider
    # Nothing to do for this provider
    return True


def getNordVPNProfiles(vpn_provider):
    # Return selectable profiles, with alias to store and message
    # Not supported for this provider
    return [], [], ""


def regenerateNordVPN(vpn_provider):
    # There's nothing to do here as everything is generated dynamically
    return True


def resetNordVPN(vpn_provider):
    # Clear out logon info to force authentication to happen again
    # Elsewhere the ovpn and location downloads will be deleted
    resetTokens()
    return True


def postConnectNordVPN(vpn_provider):
    # Post connect, might need to update the systemd config
    addon = xbmcaddon.Addon(getID())
    if ((addon.getSetting("1_vpn_validated") == getVPNProfile()) and (addon.getSetting("vpn_connect_before_boot") == "true")):
        if xbmcvfs.exists(getSystemdPath("openvpn.config")) or fakeSystemd():
            copySystemdFiles()
    return

