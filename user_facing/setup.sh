#!/bin/bash

# SET UP DIRECTORY STRUCTURE AND PULL IN ANSIBLE INITIAL SETUP 
DIR_RESOURCE_POOL="/etc/resource_pool"
DIR_ANSIBLE="${DIR_RESOURCE_POOL}/ansible"
DIR_ANSIBLE_PLAYBOOKS="${DIR_ANSIBLE}/playbooks"
DIR_POOL_TEMPLATE="${DIR_ANSIBLE}/pool_template"
GIT_BASE_URL="https://raw.githubusercontent.com/glaracuente/resource_pool_cli/master" 

mkdir "${DIR_RESOURCE_POOL}"
mkdir "${DIR_ANSIBLE}"
mkdir "${DIR_ANSIBLE}/keys"

mkdir "${DIR_ANSIBLE_PLAYBOOKS}"
URL_ANSIBLE_PLAYBOOKS="${GIT_BASE_URL}/ansible/playbooks"
for playbook in drain reset install_k8s setup_master setup_k8s_dashboard; do
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
DOCKER_IMG="glaracuente/resource_pool:latest"
docker pull ${DOCKER_IMG}

# GENERATE SSH KEYS THAT WILL BE USED BY ANSIBLE
docker run -it --entrypoint="" -v ${DIR_ANSIBLE}/keys/:/root/.ssh/ ${DOCKER_IMG} /usr/bin/ssh-keygen -f /root/.ssh/id_rsa -t rsa -N ''
chmod 400 ${DIR_ANSIBLE}/keys/*

# FETCH THE RESOURCE POOL WRAPPER SCRIPT
wget ${GIT_BASE_URL}/user_facing/resource_pool.sh -O "${DIR_RESOURCE_POOL}/resource_pool.sh"
chmod 755 "${DIR_RESOURCE_POOL}/resource_pool.sh"

# LET USER KNOW NEXT STEPS
echo "The resource_pool utility is now available at /etc/resource_pool/resource_pool.sh. Before using, you should:"
echo ""
echo "1) Add the contents of /etc/resource_pool/ansible/keys/id_rsa.pub to /root/.ssh/authorized_keys on all servers you would like to use for this set of infrastructure."
echo ""
echo "2) Add the IP addresses of these servers to /etc/resource_pool/ansible/pools/fleet/hosts.yml"
