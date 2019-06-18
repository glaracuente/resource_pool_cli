# resourcer
Insight DevOps project


./resource_pool list

./resource_pool create [NAME] -c <CORES> -m <Memory>
  
./resource_pool resize [NAME] -c <CORES> -m <Memory>
  
./resource_pool destroy [NAME]

REAL EXAMPLE:

root@ip-172-31-87-26:~# docker run -it -v /var/tmp/ansible/:/etc/ansible -v /var/tmp/keys/:/root/.ssh/ resource_pool show frontend

4 free cores in frontend pool
7900 free MB of ram in frontend pool


Terraform is used to spin up EC2 instances running vanilla Ubuntu images in a single VPC
This will represent physical servers within the same VLAN in a Data Center. 

When the user creates a RP (Resource Pool), they are creating a k8s cluster. 
The RP CLI will then scan the servers, figure out how many are needed to create a k8s master
and worker nodes to achieve the desired number of cores and memory. 

If an EC2 instance dies (simulating a physical server crash), then the RP Scheduler will 
notice the drop in resources, and add a new EC2 instance to the k8s cluster. 

Ansible will be used for provisioning the k8s master and workers.

Port scanning will be used to understand the real physical resources in the data center that
the RP CLI will use for provisioning resources. 

The Scheduling mechanism is still a work in progress, but this may be a task for Jenkins. 
