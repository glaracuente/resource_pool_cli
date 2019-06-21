#!/bin/bash

# PREREQS - docker, wget

VERSION="develop" # or master

# SET UP DIRECTORY STRUCTURE AND PULL IN ANSIBLE INITIAL SETUP 
# RECOMMEND USER TO MOUNT THIS AS NFS OR USE RAID AND TREAT AS CRITICAL
# MAYBE BETTER WAY TO PACKAGE UP ALL OF THIS (BUT WANT TO KEEP IT DISTRO AGNOSTIC)
DIR_RESOURCE_POOL="/etc/resource_pool"
DIR_ANSIBLE="${DIR_RESOURCE_POOL}/ansible"
DIR_ANSIBLE_PLAYBOOKS="${DIR_ANSIBLE}/playbooks"
DIR_POOL_TEMPLATE="${DIR_ANSIBLE}/pool_template"
GIT_BASE_URL="https://raw.githubusercontent.com/glaracuente/resourcer/${VERSION}" #NEED TO CHANGE ALL DEVELOP TO MASTER

mkdir "${DIR_RESOURCE_POOL}"
mkdir "${DIR_ANSIBLE}"
mkdir "${DIR_ANSIBLE}/keys"

mkdir "${DIR_ANSIBLE_PLAYBOOKS}"
URL_ANSIBLE_PLAYBOOKS="${GIT_BASE_URL}/ansible/playbooks"
for playbook in drain reset install_k8s setup_master; do
    wget "${URL_ANSIBLE_PLAYBOOKS}/${playbook}.yml" -O "${DIR_ANSIBLE_PLAYBOOKS}/${playbook}.yml"
done

mkdir "${DIR_POOL_TEMPLATE}"
URL_POOL_TEMPLATE="${GIT_BASE_URL}/ansible/pool_template"
for template_file in join masters workers; do
    wget "${URL_POOL_TEMPLATE}/${template_file}.yml" -O "${DIR_POOL_TEMPLATE}/${template_file}.yml"
done

mkdir "${DIR_ANSIBLE}/pools"
mkdir "${DIR_ANSIBLE}/pools/fleet"
URL_FLEET="${GIT_BASE_URL}/ansible/pools/fleet"
wget "${URL_FLEET}/hosts.yml" -O "${DIR_ANSIBLE}/pools/fleet/hosts.yml"

# PULL THE RESOURCE_POOL DOCKER IMAGE
docker pull glaracuente/resource_pool:${VERSION}

# GENERATE SSH KEYS THAT WILL BE USED BY ANSIBLE
docker run -it --entrypoint="" -v ${DIR_ANSIBLE}:/etc/ansible -v ${DIR_ANSIBLE}/keys/:/root/.ssh/  glaracuente/resource_pool:${VERSION} /usr/bin/ssh-keygen -f /root/.ssh/id_rsa -t rsa -N ''
chmod 400 ${DIR_ANSIBLE}/keys/*

# fetch the actual resource_pool wrapper  .....need to turn this into a pip install
wget ${GIT_BASE_URL}/user_facing/resource_pool.sh -O "${DIR_RESOURCE_POOL}/resource_pool.sh"

echo "The resource_pool utility is now available at /etc/resource_pool/resource_pool.sh. Before using, you should:\n"

echo "1) Add the contents of /etc/resource_pool/ansible/keys/id_rsa.pub to /root/authorized_keys all servers you would like to use for this set of infrastructure."
echo "2) Add IP addresses of these servers to /var/tmp/ansible/fleet/hosts"
# NEED TO ACTUALLY LET THEM PUT IT IN CSV OR NEWLINE FORMAT, AND GIVE THEM SCRIPT TO ADD TO FLEET_HOSTS FILE IN PROPER YAML...server_transfer.sh
