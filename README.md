Resource Pool CLI by Gerardo Laracuente

## Project Summary:

This is a cli tool written in Python for automatically creating, resizing, and destroying Kubernetes clusters. It considers these clusters as resource pools that can be described in terms of cores and memory.

This was my DevOps fellowship project as part of the Insight Data Science Summer 2019 cohort. 

*I am not the original author of then files inside of the "docker" and "k8s_dashboard" directories. I merely edited them to suit the needs of this project. All other files were written by me from scratch. 


## Why Resource Pool CLI?:

Whether it's due to costs or regulations, not everyone can run in the cloud, but that doesn’t mean you can’t be just as agile as those who do. There are 2 main issues with managing on-premise servers. 1). Reliability suffers due to server failures. 2) New features are held back due to the long purchase/install cycle for new servers.

We need to stop babysitting individual servers, and begin to think in terms of total cores and memory. My command line tool enables a team to request their resources in these terms, and all the heavy lifting is handled for them. Within minutes, they will have a Kubernetes cluster to deploy their services on, which they can also resize as needed. 

NEED TO INSERT ADVANTAGES PICS HERE

## What's going on under the hood?:

It uses Ansible to take actions on a fleet of servers. Ansible and Python are wrapped 

Python CLI > Ansible > Kubernetes Clusters


NEED TO INSERT ARCH PICS HERE

## Demo:   

[![Resource Pool CLI](http://img.youtube.com/vi/WlnvPHdo3xs/0.jpg)](http://www.youtube.com/watch?v=WlnvPHdo3xs "Resource Pool CLI")


## Project Challenges:

NEED TO LIST CHALLENGES HERE

## Future Work:

Auto-Healing

HA

Alerts

Metal LB
Stateful Apps
