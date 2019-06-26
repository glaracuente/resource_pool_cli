#!/bin/bash

RESOURCE_CLI_ARGS="$@"

if [[ $# -eq 0 ]] ; then
    RESOURCE_CLI_ARGS="-h"
fi

VERSION="develop"

DIR_RESOURCE_POOL="/etc/resource_pool"
DIR_ANSIBLE="${DIR_RESOURCE_POOL}/ansible"

docker run -it -v ${DIR_ANSIBLE}:/etc/ansible -v ${DIR_ANSIBLE}/keys/:/root/.ssh/ glaracuente/resource_pool:${VERSION} ${RESOURCE_CLI_ARGS}
