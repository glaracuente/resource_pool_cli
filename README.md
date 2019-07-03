__Resource Pool CLI__ by Gerardo Laracuente

## Project Summary:

This is a cli tool written in Python for automatically creating, resizing, and destroying Kubernetes clusters. It regards these clusters as resource pools that can be described in terms of cores and memory.

This was my DevOps fellowship project as part of the Insight Data Science Summer 2019 NYC cohort. 

*I am not the original author of then files inside of the "docker" and "k8s_dashboard" directories. I merely edited them to suit the needs of this project. All other files were written by me from scratch. 


## Why Resource Pool CLI?:

Whether it's due to costs or regulations, not everyone can run in the cloud, but that doesn’t mean you can’t be just as agile as those who do. There are 2 main issues with managing on-premise servers. 1). Reliability suffers due to server failures. 2) New features are held back due to the long purchase/install cycle for new servers.

We need to stop babysitting individual servers, and begin to think in terms of total cores and memory. My command line tool enables a team to request their resources in these terms, and all the heavy lifting is handled for them. Within minutes, they will have a Kubernetes cluster to deploy their services on, which they can also resize as needed. 

<<<<<<<<<<<<<<< NEED TO INSERT ADVANTAGES PICS HERE >>>>>>>>>>>>>>>

## What's going on under the hood?:

Python CLI > Ansible > Servers = Kubernetes Clusters

The CLI is written in Python, but is powered by Ansible. Ansible playbooks contain the instructions to create new kubernetes clusters, add nodes, drain and delete nodes, etc. 

<img src= img/Arch.png width="600" height="400" >

In the top half of the archtecture diagram, I show what this would look like in the real world. The user would just need to have one server running docker. After running one simple bash script, everything will be set up for them. This server becomes the "captain" server, which runs the CLI alongside Ansible inside of a docker container. 

The bottom half shows what was used for development, and you can try this out yourself. I used Terraform to spin up mock "data centers" in AWS. These are just EC2 instances running Ubuntu 16.04. I run the setup.sh script on one of them, and then use that "captain" instance to create k8s clusters out of the others. 

## Demo:   

[![Resource Pool CLI](http://img.youtube.com/vi/WlnvPHdo3xs/0.jpg)](http://www.youtube.com/watch?v=WlnvPHdo3xs "Resource Pool CLI")


## Project Challenges:

__Unique token/hash per cluster__ - Each k8s clusters requires a unique token and hash for a worker node to join it. To address this, I use ansible to get this token/hash from the master, and then dynamically create a "join" playbook that is unique to each cluster. 

__Resizing clusters__ - A user may ask to decrease a pool by 24 cores, but the reality with bare-metal servers is that some servers can have 24 cores and 32 GB of ram, while other have 12 cores and 256 GB of ram. In most cases, the GB of ram will be higher than the core count, so I chose to sort the available servers in decreasing order or core count, unless the user is specifically looking for a large memory change. The user is also warned about the potential change before changes occur. 

__Total lifeycle of servers__ - During the lifecycle of a server, it can be a k8s master, worker node, or generally available server in the fleet of hardware. With that in mind, I made sure that everytime a server is returned to the fleet, all of the k8s configs are reset, and before a server try to join a k8s cluster, I check that it has the proper packages installed. I began the project using INI files for the ansible inventory, but since I need to transer servers so often, I found that YAML was a better format, and I had to refactor my code to handle this change. 

## Future Work:

__Auto Healing__ - A scheduler needs to keep track of the desired resource counts for each pool. When a server goes down, the scheduler should notice the decrease in resources, and automatically replace the serve and notify an admin, create a ticket, etc. 

__HA of Masters__ - The master of each cluster is currently a point of failure. The master should be a set of servers set up for HA.

__Load Balancer__ - Since this should be able to run on baremetal, "Metal LB" needs to be added to the cluster in order to expose services properly. NodePort is currently used, but this is not a production ready method. 
