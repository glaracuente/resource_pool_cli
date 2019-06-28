#!/bin/bash

RESOURCE_CLI_ARGS="$@"

if [[ $# -eq 0 ]] ; then
    RESOURCE_CLI_ARGS="-h"
fi

DIR_ANSIBLE="/etc/resource_pool/ansible"

docker run -it -v ${DIR_ANSIBLE}:/etc/ansible -v ${DIR_ANSIBLE}/keys/:/root/.ssh/ glaracuente/resource_pool:latest ${RESOURCE_CLI_ARGS}
