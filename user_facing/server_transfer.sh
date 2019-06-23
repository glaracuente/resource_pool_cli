#!/bin/bash

#ACTION=$1
#ACTION SHOULD BE LIST, ADD, REMOVE, with careful checks not to remove servers in use as pool resources, and check for dupes before adding

#THE INPUT CAN BE CSV on cmd line, CSV FILE, or file of IPS on each line

#ACTION-LIST
#DO THE BELOW FOR EVERY FILE IN POOLS_DIR, and just echo out the IPs that are in the fleet, and the ones in use
YAMLFILE="/Users/gerry/Desktop/hosts_sample"
IPS=`grep -E -o "([0-9]{1,3}[\.]){3}[0-9]{1,3}" ${YAMLFILE}`
echo $IPS
#THEN ADD TO THE FLEET FILE


#ACTION-ADD
#DO THE BELOW FOR EVERY FILE IN POOLS_DIR, and make sure user is not adding a server that is already there
YAMLFILE="/Users/gerry/Desktop/hosts_sample"
IPS=`grep -E -o "([0-9]{1,3}[\.]){3}[0-9]{1,3}" ${YAMLFILE}`
echo $IPS
#THEN ADD TO THE FLEET FILE


#ACTION-REMOVE
#REMOVE THE INPUT OF IPS from the FLEET FILE ONLY