#!/bin/sh
iptables -F
iptables -A INPUT -i tun0 -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -A INPUT -i tun0 -j DROP
