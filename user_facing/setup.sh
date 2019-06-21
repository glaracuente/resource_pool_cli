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
for playbook in destroy drain k8s; do
    wget "${URL_ANSIBLE_PLAYBOOKS}/${playbook}" -O "${DIR_ANSIBLE_PLAYBOOKS}/${playbook}"
done

mkdir "${DIR_POOL_TEMPLATE}"
URL_POOL_TEMPLATE="${GIT_BASE_URL}/ansible/pool_template"
for template_file in hosts join; do
    wget "${URL_POOL_TEMPLATE}/${template_file}" -O "${DIR_POOL_TEMPLATE}/${template_file}"
done

mkdir "${DIR_ANSIBLE}/pools"
mkdir "${DIR_ANSIBLE}/pools/fleet"
URL_FLEET="${GIT_BASE_URL}/ansible/pools/fleet"
wget "${URL_FLEET}/hosts" -O "${DIR_ANSIBLE}/pools/fleet/hosts"



# PULL THE RESOURCE_POOL DOCKER IMAGE
docker pull glaracuente/resource_pool:${VERSION}

# GENERATE SSH KEYS THAT WILL BE USED BY ANSIBLE
docker run -it --entrypoint="" -v ${DIR_ANSIBLE}:/etc/ansible -v ${DIR_ANSIBLE}/keys/:/root/.ssh/  glaracuente/resource_pool:${VERSION} /usr/bin/ssh-keygen -f /root/.ssh/id_rsa -t rsa -N ''
chmod 400 ${DIR_ANSIBLE}/keys/*


# wget the actual resource bash script as /etc/resource_pool/resource_pool .....or pip install it
#wget ${GIT_BASE_URL}/resource_pool_cli/resource_pool -O "${DIR_RESOURCE_POOL}/resource_pool" #THIS IS THE BASH WRAPPER
# which will just run docker run -it -v /etc/resource_pool/ansible/:/etc/ansible -v /etc/resource_pool/keys/:/root/.ssh/ glaracuente/resource_pool:develop 

# PROMPT USER TO ADD THIS KEY TO AUTH KEYS FOR THEIR SERVERS /root/authorized_keys
# PROMPT USER TO ADD /etc/resource_pool to their path
# LET THEM KNOW IT CAN NOW BE RUN WITH /etc/resource_pool/resource_pool


# Puts [k8s] and private IPs of ec2 instances in /var/tmp/ansible/fleet/hosts file (need better way for this also...use aws cli parsing)
#     touch /var/tmp/server_ips
#     transofrm them into /var/tmp/ansible/pools/fleet/hosts.yaml