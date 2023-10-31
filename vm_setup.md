## Virtual Machine Preparations

We will create a virtual machine following these steps:

Prepare a KVM template with the following CentOS release:
centos-release-7-9.2009.1.el7.centos.x86_64

The xml files containing the detailed configurations can be found in the "VM_configurations" folder.

Within the VM, execute the following:

1) Prepare Python Virtual Environment:
yum install -y python3 python3-devel zlib-devel libjpeg-devel gcc bzip2
python(3.6.8) -m venv generator/
source generator/bin/activate
pip install wheel numpy cython pandas networkx jinja2 matplotlib scipy paramiko
pip install --upgrade pip
mkdir src
cd src
git clone https://github.com/nrodday/bgpReader_util
cd bgpReader_util/
python setup.py install

2) Install docker (20.10.18, build b40c2f6):
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install docker-ce docker-ce-cli containerd.io docker-compose-plugin nano htop net-tools
systemctl enable docker
systemctl start docker

3) Download newest AS-rel CAIDA files
mkdir data
cd data
wget https://publicdata.caida.org/datasets/as-relationships/serial-2/20221001.as-rel2.txt.bz2
bzip2 -d 20221001.as-rel2.txt.bz2

4) Obtain BGP dump for 24h:
bgpreader -w 1664575200,1664661599 -m > 1664575200_1664661599.txt &

5) Clone and deploy NIST framework
use install script from https://github.com/usnistgov/NIST-BGP-SRx/blob/master/INSTALL.md


6) Create bgpd.conf files in quagga-srx/bgpd/
7) Create zebra.conf files in quagga-srx/zebra/
8) Modify docker_compose.yml with 
	a) Add volume for zebra: - ./quagga-srx/zebra/zebra.conf.sampleSRx_4:/usr/etc/zebra.conf
	b) stop exposing ports by uncommenting
	c) Add zebra execution: zebra -u root -f /usr/etc/zebra.conf
	d) Change IP addresses accordingly
9) Start containers with "docker compose up"
10) Connect to single docker instance with "docker exec -it NAME bash"
11) Configure quagga with
	a) telnet localhost 2605 (pw zebra)
	b) enable, configure terminal, router bgp 7672 > network x.y.z.0/24 (this will be announced to peers)
	c) enable, show running config: "show running-config"
	d) Summary: "sh ip bgp summary"
	e) Prefixes: "sh ip bgp ipv4 unicast"
12) To make prefix respondable add IP to loopback interface: "sudo ip addr add 203.0.113.1 dev lo" (now host B should be able to access a prefix announced by host A)

VMs need to be able to reserve the assgined RAM on host machine. Do not assgin two VMs 8GB each and run both, it will crash.


Set hostname on worker nodes:
hostnamectl set-hostname my.new-hostname.server

Increase MaxStartups attribute in /etc/ssh/sshd_config on all nodes:
MaxStartups 30:50:100
systemctl restart sshd

Disable SELinux to avoid interference in /etc/selinux/config:
SELINUX=disabled

Set static IP in KVM manager for manager machines:
1) find MAC of Guest
2) virsh net-dumpxml default
3) Edit file and add entry for manager node
4) Restart KVM: sudo systemctl restart libvirtd.service

Docker Swarm Manager:
Create internal network interfaces for VMs
Give them static IPs in 10.0.1.x
Change /etc/docker/daemon.json to (insecure registry):
{
  "bip": "172.17.0.1/16",
  "default-address-pools":[
    {"base":"172.17.0.0/16","size":24},
    {"base":"172.18.0.0/16","size":16}
  ],
  "insecure-registries":["10.0.1.1:5000"]
}
or 192.168.122.2

Allow docker on all nodes (add interface for docker traffic to trusted zone):
firewall-cmd --permanent --zone=trusted --change-interface=ens10
firewall-cmd --reload

Initialize Docker swarm on manager:
docker swarm init --advertise-addr 10.0.1.1

Join swarm on worker nodes:
docker swarm join --token SWMTKN-1-335wqlqbj2jhxu5ojh5dg98lh4is7reoqve8leh0f35tgbm2wt-7dqzxp3xmxt2m2bgxoubx9din 10.0.1.1:2377

Drain manager node (to not execute production containers):
docker node update --availability drain nist_1

Modify Dockerfile and add screen to install commands
nano Dockerfile
%% Add screen and net-tools to installs
Add Entrypoint to file:
ENTRYPOINT ./start_rpkirtr.sh
OR
ENTRYPOINT ./start_as.sh

Provide files in the same directory (found in docker_configuarions folder).

Make files 777 executable!
chmod 777 start_rpkirtr.sh start_as.sh

Create one docker image for rpkirtr_server with start_rpkirtr.sh and one image for the ASes with start.sh:
docker build -t rpkirtr_v1 .
docker build -t ascones_v1 .

Deploy local registry:
docker run -d -p 5000:5000 --restart=unless-stopped --name registry registry:2

Tag dockerimage with ip:port:
docker image tag rpkirtr_v1:latest ip_of_repository:5000/rpkirtr_v1
docker image tag ascones_v1:latest ip_of_repository:5000/ascones_v1

Push image on registry host:
docker image push ip_of_repository:5000/rpkirtr_v1
docker image push ip_of_repository:5000/ascones_v1

Fetch image on ALL nodes from repository:
docker pull ip_of_repository:5000/rpkirtr_v1
docker pull ip_of_repository:5000/ascones_v1

Create Overlay Network for Docker container on manager:
docker network create -d overlay --subnet=172.28.0.0/14 --attachable bgp_net

The template VM file for the workers has a crontab installed (crontab -l) that sets the hostname and joins the swarm.



When copying the xml for a VM from CentOS to Ubuntu make sure to change the emulator path in the xml
Replace <cpu> section in XML file from VM with cpu of host

A normal KVM user cannor attach to bridge interfaces created by root, also not if within virsh net a network was defined for the OpenvSwitch. We have to work as a root user.