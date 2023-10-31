## Hardware Machines Preparations
Execute on all hosts:
sudo apt -y install bridge-utils cpu-checker libvirt-clients libvirt-daemon qemu qemu-kvm virtinst libvirt-daemon-system
sudo apt install openvswitch-switch uml-utilities

Edit OpenSSH config and add tunnel forwarding and TCP forwarding:
nano /etc/ssh/sshd_config
AllowTcpForwarding yes
PermitTunnel yes

Check that net.ipv4.ip_forward is set to 1.

Create SSH RSA Keypair and distribute on cluster server nodes.

### Create tunnels between servers

Execute on server1 for SSH reachability (note remote port!):
ssh -i /home/username/.ssh/server1 -N -T -f -R 2223:127.0.0.1:2222 username@server1
Execute on server2 for SSH reachability
ssh -i /home/username/.ssh/server2 -N -T -f -R 2222:127.0.0.1:2222 username@server1

Set cap_net_admin capability for user on remote side of tunnel (local has to be executed with root when instanciating tunnel):
nano /etc/security/capability.conf
cap_net_admin username
cap_net_raw username

Add pam_cap.so to authentification:
nano /etc/pam.d/su
auth        optional    pam_cap.so

Logout/login and check that capability was correctly set for user with 
capsh --print
It must say: 
Current: = cap_net_admin+i

Spawn tunnel interfaces on both sides for first tunnel (server1/server2):
tunctl -t tap0 -u username

Connect via SSH tunnelling (from server1 to server2): 
ssh -X -N -T -f -o Tunnel=ethernet -w 0:0 username@127.0.0.1 -p 2222

Spawn tunnel interfaces on both sides for second tunnel (server2/server3):
tunctl -t tap1 -u username

Connect via SSH tunnelling (from server2 to server3): 
ssh -X -N -T -f -o Tunnel=ethernet -w 1:1 username@server3 -p 2222

### Check connectivity, latency, and bandwidth

Server:
iperf -s -p 15001 -B 192.168.0.1
Client:
iperf -c 192.168.0.1 -p 15001 -t 30 -bidir

### Create OpenvSwitch layer2 tunnel

As root, create on each hypervisor host:
1) SSH Tunnel with port forwarding
2) Socat tap interfaces
3) ovs-vsctl add-br br0
4) (optional) Enable Spanning tree to avoid loops:
ovs-vsctl set bridge br0 stp_enable=true
5) Check STP config with: 
ovs-appctl stp/show
4) Set IP for bridge on each host:
ip addr add 192.168.0.{1,2}/24 dev br0
ip link set br0 up

Make sure all tap interfaces are also UP
ip link set tap0 up

Add ports to the OVS bridge on each host:
4) ovs-vsctl add-port br0 tap0
5) fill ovsnet.xml with:
<network>
<name>ovs-br0</name>
<forward mode='bridge'/>
<bridge name='br0'/>
<virtualport type='openvswitch'/>
</network>
6) virsh net-list --all
7) virsh net-define ovsnet.xml
8) virsh net-start ovs-br0
9) virsh net-autostart ovs-br0
10) In the VM template, add an extra NIC with the ovs-br0 interface
11) Change the default network on each host to allow for more VMs to be spawned (one they get killed and spawned, leases might be longer and the host runs out of IPs it can hand out):
virsh net-edit default

<network>
  <name>default</name>
  <uuid>33bbad10-8a98-41d7-923c-d04a092d1234</uuid>
  <forward mode='nat'/>
  <bridge name='virbr0' stp='on' delay='0'/>
  <mac address='52:54:00:36:db:9d'/>
  <ip address='192.168.112.1' netmask='255.255.224.0'>
    <dhcp>
      <range start='192.168.122.2' end='192.168.127.254'/>
      <host mac='52:54:00:7d:75:e4' name='nist_1' ip='192.168.122.2'/>
    </dhcp>
  </ip>
</network>

Restart network to take effect:
virsh net-destroy default
virsh net-start default

To avoid an overlap, we will use
192.168.0.0 / 19 -> OpenvSwitch bridge interface
192.168.122.0 / 19 -> KVM bridge interface

After performing the operations above, we should have X servers set up with tunnel in-between each other. Via these tunnels, we run an OpenvSwitch overlay network that interconnects the hardware machines and (later on) the VMs.