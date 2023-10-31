#!/bin/bash
virsh list --all | grep -o -E "(nist_centos7_worker\w*)" | \
xargs -P 20 -I % sh -c 'virsh destroy % && virsh undefine % && rm -rf /data/VMs/%.qcow2'
