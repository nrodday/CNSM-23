#!/bin/bash
sed "s/localhost/172.30.0.101/g"  /usr/etc/srx_server.conf > /tmp/srx_server.conf
sed "s/srx connect/srx connect 127.0.0.1 17900/g" /usr/etc/bgpd.conf > /etc/bgpd.conf
sleep 120
srx_server -f /tmp/srx_server.conf &
sleep 5
bgpd -u root -f /etc/bgpd.conf &
zebra -u root -f /usr/etc/zebra.conf