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
#    Shared code to return info about an IP connection.

import re
import urllib2


ip_sources = ["Auto select", "IP-API", "IPInfoDB", "freegeoip.net"]
ip_urls = ["", "http://ip-api.com/json", "http://www.ipinfodb.com/my_ip_location.php", "http://freegeoip.net/json/"] 


def getIPInfoFrom(source):
    # Generate request to find out where this IP is based
    # Successful return is ip, country, region, city, isp 
    # No info generated from call is "no info", "unknown", "unknown", "unknown", url response
    # Or general error is "error", "error", "error", reason, url response
    link = ""
    try:      
        # Determine the URL, make the call and read the response
        url = getIPSourceURL(source)
        if url == "": return "error", "error", "error", "unknown source", ""
        req = urllib2.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:38.0) Gecko/20100101 Firefox/38.0")
        response = urllib2.urlopen(req)
        link = response.read()
        response.close()
        
        #print link
        
        # Call the right routine to parse the reply using regex.
        # If the website changes, this parsing can fail...sigh
        if source == "IPInfoDB": match = getIPInfoDB(link)
        if source == "IP-API": match = getIPAPI(link)
        if source == "freegeoip.net": match = getFreeGeoIP(link)
        if len(match) > 0:
            for ip, country, region, city, isp in match:
                return ip, country, region, city, isp
        else:            
            return "no info", "unknown location", "unknown location", "no matches", link
    except:
        return "error", "error", "error", "call failed", link


def getIPAPI(link):
    match = re.compile(ur'"city":"(.*?)".*"country":"(.*?)".*"isp":"(.*?)".*"query":"(.*?)".*"regionName":"(.*?)"').findall(link)
    if len(match) > 0:
        for city, country, isp, ip, region in match:
            return [(ip, country, region, city, isp)]
    else:
        return None           
        
        
def getIPInfoDB(link):
    match = re.compile(ur'<h5>Your IP address.*</h5>.*\s*.*<br>.*IP2Location.*\s*.*\s*<li>IP address.*<strong>(.+?)</strong>.*\s*\s*<li>Country : (.+?) <img.*\s*<li>State.*: (.+?)</li>.*\s*<li>City : (.+?)</li>').findall(link)    
    if len(match) > 0:
        for ip, country, region, city in match:
            return [(ip, country, region, city, "Unknown")]
    else:
        return None

        
def getFreeGeoIP(link):
    match = re.compile(ur'"ip":"(.*?)".*"country_name":"(.*?)".*"region_name":"(.*?).*"city":"(.*?)".*').findall(link)
    if len(match) > 0:
        for ip, country, region, city in match:
            return [(ip, country, region, city, "Unknown")]
    else:
        return None

        
def getIPSources():
    return ip_sources


def getIPSourceURL(source):
    i = 0
    for name in ip_sources:
        if name == source:
            return ip_urls[i]
        i = i + 1
    return ""        


def getNextSource(current_source):
    next = ip_sources.index(current_source)
    next = next + 1
    if next == len(ip_sources): next = 1
    return ip_sources[next]
    
    
def getAutoSource():
    return ip_sources[1]

    