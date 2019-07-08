__Resource Pool CLI__ by Gerardo Laracuente

## Project Summary:

This is a cli tool written in Python for automatically creating, resizing, and destroying Kubernetes clusters. It regards these clusters as resource pools that can be described in terms of cores and memory.

This was my DevOps fellowship project as part of the Insight Data Science Summer 2019 NYC cohort. 

*I am not the original author of the files inside of the "docker" and "k8s_dashboard" directories. I merely edited them to suit the needs of this project. All other files were written by me from scratch. 


## Why Resource Pool CLI?:

Whether it's due to costs or regulations, not everyone can run in the cloud, but that doesn’t mean you can’t be just as agile as those who do. There are 2 main issues with managing on-premise servers. 1). Reliability suffers due to server failures. 2) New features are held back due to the long purchase/install cycle for new servers.

We need to stop babysitting individual servers, and begin to think in terms of total cores and memory. My command line tool enables a team to request their resources in these terms, and all the heavy lifting is handled for them. Within minutes, they will have a Kubernetes cluster to deploy their services on, which they can also resize as needed. 


## What's going on under the hood?:

Python CLI > Ansible > Servers = Kubernetes Clusters

The CLI is written in Python, but is powered by Ansible. Ansible playbooks contain the instructions to create new kubernetes clusters, add nodes, drain and delete nodes, etc. 

<p align="center">
<img src= img/arch.png width="700" height="400">
</p>

In the top half of the archtecture diagram, I show what this would look like in the real world. The user would just need to have one server running docker. After running one simple bash script, everything will be set up for them. This server runs the CLI alongside Ansible inside of a docker container. 

The bottom half shows what was used for development, and you can try this out yourself. I spun up mock "data centers" in AWS. These are just EC2 instances running Ubuntu 16.04, in the same VPC. I run the setup.sh script on one of them, and then use this instance to create k8s clusters out of the others. 


## Demo:   

[![Resource Pool CLI](http://img.youtube.com/vi/WlnvPHdo3xs/0.jpg)](http://www.youtube.com/watch?v=WlnvPHdo3xs "Resource Pool CLI")

Want to try it out? 
- All you need is the __setup.sh__ file from the __user_facing__ directory. 
- The server for running the CLI needs to have docker installed before running the setup script. 
- This entire project has only been tested on Ubuntu 16.04. 


## Future Work:

__Auto Healing__ - A scheduler needs to keep track of the desired resource counts for each pool. When a server goes down, the scheduler should notice the decrease in resources, and automatically replace the server and notify an admin, create a ticket, etc. 

__HA of Masters__ - The master of each cluster is currently a point of failure. The master should be a set of servers set up for HA.

__Load Balancer__ - Since this should be able to run on baremetal, "Metal LB" needs to be added to the cluster in order to expose services properly. NodePort is currently used, but this is not a production ready method. 
