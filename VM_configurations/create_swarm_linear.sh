#!/bin/bash
while getopts n:p: OPTION; do
  case "$OPTION" in
    n)
      nvalue="$OPTARG"
      echo "Spawning $nvalue VMs"
      ;;
    p)
      pvalue="$OPTARG"
      echo "Path of VMs: $pvalue"
      ;;
    ?)
      echo "script usage: $(basename \$0) [-n number_of_vms] [-p path_to_VMs]" >&2
      exit 1
      ;;
  esac
done
shift "$(($OPTIND -1))"

counter=1
nvalue=$(( nvalue + 1 ))
while [ $counter -lt $nvalue ]
do
        virt-clone --original nist_centos7_template -n nist_centos7_worker$counter -f $pvalue/nist_centos7_worker$counter.qcow2 --auto-clone --check path_exists=off && virsh start nist_centos7_worker$counter
        ((counter++))
done