# CNSM 2023 Artifacts

This repository contains artifacts for the CNSM'23 submission. We provide scripts and instructions for three parts. First, the configuration of OpenvSwitch for multiple hardware machines via SSH (server_setup.md). Second, the creation of the KVM virtual machines (VMs), one manager and one worker VM, which are later on replicated when the testbed is scaled (VM_setup.md). Third, within the VMs, we need a docker image containing the NIST BGP-SRx software suite.

We are also able to provide the readily configured manager and worker VMs including the readily configured docker images (nils.rodday@unibw.de). The instructions in the READMEs are for technical users that would like to create the testbed themselves and want to be able to adapt it to their needs.

If you plan on using the VMs, you only need to do the OpenvSwitch configuration of the hardware machines and simply import the VMs onto the cluster nodes.

## Execution of BGPEval after configuration


Scale the testbed to an appropriate size by replicating worker VMs according to the respective servers capacity:

./create_swarm_linear.sh -n 55 -p /data/VMs/

You might need to adjust the paths inside the scripts according to your setup. Execute this on each cluster node.

After the VMs are replicated, the worker nodes automatically join the manager VMs Docker swarm. 

You can run BGPEval by calling the generator.py file inside the manager VM. It will result in the /confd directory filling with 
1) the config files for all ASes within the provided input graph.
2) zebra.conf (which is the same in each container)
3) router_ids.json (a database of mapped IPs)

To make the swarm deploy our predefined docker images run the following inside the manager VM:

stack_deploy.py

It will take quite some time (actually hours, depending on your hardware) till the network converges to a stable testbed.

To remove Docker services and clean the testbed use:

stack_prune.py

Alternatively, to destroy the whole testbed including the hosting VMs, you can run the followig from the servers hosting the VMs:

./destroy_swarm.sh

