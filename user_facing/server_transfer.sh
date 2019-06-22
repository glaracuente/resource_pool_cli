#!/bin/bash

ACTION=$1

#ACTION SHOULD BE LIST, ADD, REMOVE, with careful checks not to remove servers in use as pool resources, and check for dupes before adding

#YAMLFILE="./fleet/hosts"
#TEXT=`cat ${YAMLFILE}`
#HOSTS=`echo ${TEXT} | sed -e 's/.*{\(.*\)}.*/\1/'`

