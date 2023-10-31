import json
import os
import subprocess
from re import search
import time
from multiprocessing import Pool
import sys
import paramiko

node_ips = {}
rpkirtr_image_name = '192.168.0.10:5000/rpkirtr_v1'
#as_image_name = '192.168.0.10:5000/ascones_v1'
as_image_name = '192.168.0.10:5000/gobgp_v5'
username='root'
password='nist'
ssh_sessions = {}
manager_ip = '192.168.0.10'

def create_configs(router_ids):
    command = 'docker config create zebra /opt/generator_project/confd/zebra.conf'
    # command = 'ls -la'
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
    process.wait()
    if process.returncode == 0:
        print('Created config for zebra')
    else:
        print('ERROR creating config for zebra')

    command = 'docker config create srx_server /opt/generator_project/confd/srx_server.conf'
    # command = 'ls -la'
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
    process.wait()
    if process.returncode == 0:
        print('Created config for srx_server')
    else:
        print('ERROR creating config for srx_server')

    command = 'docker config create srxcryptoapi /opt/generator_project/confd/srxcryptoapi.conf'
    # command = 'ls -la'
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
    process.wait()
    if process.returncode == 0:
        print('Created config for srxcryptoapi')
    else:
        print('ERROR creating config for srxcryptoapi')

    print('Creating swarm configs')
    with Pool(40) as p:
        p.map(create_config, router_ids)

def create_config(AS):
    if AS.isnumeric():
        command = 'docker config create AS_' + AS + ' /opt/generator_project/confd/AS_' + AS + '.conf'
        # command = 'ls -la'
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
        process.wait()
        if process.returncode == 0:
            print('Created config for AS_' + AS)
        else:
            print('ERROR creating config for AS_' + AS)

def deploy_rpkirtrt_server():
    # Deploy rpkirtr_Server container
    command = 'docker service create --name rpkirtr_server --constraint "node.role==worker" --cap-add NET_ADMIN --network bgp_net --publish 323:323 ' + rpkirtr_image_name
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
    process.wait()
    if not process.returncode == 0:
        print('ERROR deploying rpkirtr_server')
    else:
        print('Deployed rpkirtr_server')
        time.sleep(5)
        #Reassign IP
        # Find node the service is running on
        result = os.popen('docker service ps rpkirtr_server --format "{{.Node}}"').read().strip()
        # Find IP of node
        node_ip = node_ips[result]

        #        if node_ip=='10.0.1.1':
        if node_ip == manager_ip:
            command = os.popen('docker ps --format "{{.Names}}"').read()
            # print(command)
            splitted = command.splitlines()
            for s in splitted:
                if search('rpkirtr_server', s):
                    print('Found rpkirtr_server instance')
                    print(s)

                    # Disconnect interface
                    command = 'docker network disconnect bgp_net ' + s
                    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
                    process.wait()
                    if not process.returncode == 0:
                        print('ERROR disconnecting rpkirtr_server')
                    else:
                        print('Disconnected rpkirtr_server')

                        # Reconnect interface
                        command = 'docker network connect --ip 172.30.0.101 bgp_net ' + s
                        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
                        process.wait()
                        if not process.returncode == 0:
                            print('ERROR reconnecting rpkirtr_server')
                        else:
                            print('Reconnected rpkirtr_server')

        else:
            # print('SSH connection')
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # AutoAdd unknown hosts to hosts_file
            #            ssh.connect(node_ip, username='root', password='mininet')
            ssh.connect(node_ip, username=username, password=password, timeout=1000, banner_timeout=1000, auth_timeout=1000)

            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('docker ps --format "{{.Names}}"')
            result = ssh_stdout.readlines()
            # print('result', result)
            for s in result:
                if search('rpkirtr_server', s):
                    print('Found rpkirtr_server instance')
                    print(s)

                    # Disconnect interface
                    command = 'docker network disconnect bgp_net ' + s
                    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(command)
                    # print("SSH Output: ", ssh_stdout.readlines())
                    if not ssh_stdout.channel.recv_exit_status() == 0:
                        print('SSH - ERROR disconnecting ' + s)
                    else:
                        print('SSH - Disconnected ' + s)

                        # Reconnect interface
                        command = 'docker network connect --ip 172.30.0.101 bgp_net ' + s
                        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(command)
                        # print("SSH Output: ", ssh_stdout.readlines())

                        if not ssh_stdout.channel.recv_exit_status() == 0:
                            print('SSH - ERROR reconnecting ' + s)
                        else:
                            print('SSH - Reconnected ' + s)

            ssh.close()



def deploy_AS(id):
    # Deploy rpkirtr_Server container
    command = 'docker service create --name AS_'+id+' --constraint "node.role==worker" --cap-add NET_ADMIN --network bgp_net --config source=AS_'+id+',target=/usr/etc/bgpd.conf --config source=zebra,target=/usr/etc/zebra.conf --config source=srx_server,target=/usr/etc/srx_server.conf --config source=srxcryptoapi,target=/usr/etc/srxcryptoapi.conf ' + as_image_name
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
    process.wait()
    if not process.returncode == 0:
        print('ERROR deploying AS_'+id)
    else:
        print('Deployed AS_'+id)
        time.sleep(5)
        #Reassign IP

        try:
            #Find node the service is running on
            result = os.popen('docker service ps AS_'+id+' --format "{{.Node}}"').read().strip()
            #Find IP of node
            node_ip = node_ips[result]
        except:
            print('An Exception occured with the result AS: ' + result)

        else:

    #        if node_ip=='10.0.1.1':
            if node_ip == manager_ip:
                command = os.popen('docker ps --format "{{.Names}}"').read()
                splitted = command.splitlines()
                for s in splitted:

                    start = 'AS_'
                    end = '.1.'
                    extracted_part = (s[s.find(start) + len(start):s.rfind(end)])
                    if extracted_part.replace('AS_', '').isnumeric() and extracted_part==id:
                        ip = router_ids[id][0]
                        print(s)

                        #Disconnect interface
                        command = 'docker network disconnect bgp_net ' + s
                        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
                        process.wait()
                        if not process.returncode == 0:
                            print('ERROR disconnecting AS_'+s)
                        else:
                            print('Disconnected AS_'+s)

                            #Reconnect interface
                            command = 'docker network connect --ip '+ip+' bgp_net ' + s
                            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
                            process.wait()
                            if not process.returncode == 0:
                                print('ERROR reconnecting '+s)
                            else:
                                print('Reconnected '+s)

            else:
                #print('SSH connection')
                print('Node IP: ' + node_ip)
                if node_ip != manager_ip and node_ip != '' and isReady(result):
                    print('Connecting to: ' + id + " IP: " + node_ip)
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # AutoAdd unknown hosts to hosts_file
                    # ssh.connect(node_ip, username='root', password='mininet')
                    ssh.connect(node_ip, username=username, password=password, timeout=1000, banner_timeout=1000, auth_timeout=1000)


                    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('docker ps --format "{{.Names}}"')
                    result = ssh_stdout.readlines()
                    #print('result', result)
                    for s in result:
                        s = s.strip()
                        #print(s)
                        start = 'AS_'
                        end = '.1.'
                        extracted_part = (s[s.find(start) + len(start):s.rfind(end)])
                        if extracted_part.replace('AS_', '').isnumeric() and extracted_part == id:
                            ip = router_ids[id][0]
                            #print(s)

                            # Disconnect interface
                            command = 'docker network disconnect bgp_net ' + s
                            ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(command)
                            #print("SSH Output: ", ssh_stdout.readlines())
                            if not ssh_stdout.channel.recv_exit_status() == 0:
                                print('SSH - ERROR disconnecting AS_'+s)
                            else:
                                print('SSH - Disconnected AS_'+s)

                                # Reconnect interface
                                command = 'docker network connect --ip ' + ip + ' bgp_net ' + s
                                ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(command)
                                #print("SSH Output: ", ssh_stdout.readlines())

                                if not ssh_stdout.channel.recv_exit_status() == 0:
                                    print('SSH - ERROR reconnecting ' + s)
                                else:
                                    print('SSH - Reconnected ' + s)
                    ssh.close()
                else:
                    print('Not connecting to ' + result)


def get_node_ips(node_ips):
    result = os.popen('docker node ls --format "{{.Hostname}}"').read()
    splitted = result.splitlines()
    #print(splitted)
    for s in splitted:
        #print(s)
        result = os.popen('docker node inspect '+s).read()
        node_ip = result.partition('Addr": "')[2].split('"')[0]
        node_ips[s]=node_ip
    return node_ips

def isReady(id):
    print('Checking for id: ' + id)
    result = os.popen('docker node ls | grep ' + id).read()
    if 'Ready' in result: return True
    return False

def create_ssh_sessions(node_ips, manager_ip):
    for id in node_ips:
        if node_ips[id] != manager_ip and node_ips[id] != '' and isReady(id):
            print('Connecting to: ' + id + " IP: " + node_ips[id])
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # AutoAdd unknown hosts to hosts_file
            # ssh.connect(node_ip, username='root', password='mininet')
            ssh.connect(node_ips[id], username=username, password=password)
            ssh_sessions[id] = ssh
        else: print('Not connecting to ' + id)


def close_ssh_sessions(ssh_sessions):
    print('Closing ssh sessions')
    print(ssh_sessions)
    for session in ssh_sessions:
        session.close()

if __name__ == '__main__':
    print('Loading router IDs')
    io = open("confd/router_ids.json", "r")
    router_ids = json.load(io)
    print('DONE Loading router IDs')

    node_ips = get_node_ips(node_ips)
    for id, ip in node_ips.items():
        print(id, ip)

    create_configs(router_ids)

    #ssh_sessions = create_ssh_sessions(node_ips, manager_ip)
    #close_ssh_sessions(ssh_sessions)



    #We need the RPKIRTR Server at first as all other ASes will try to reach it!
    deploy_rpkirtrt_server() # Check image global variable name!

    #sys.exit()

    router_ids.pop('rpkirtr_server')
    with Pool(5) as p:
        p.map(deploy_AS, router_ids) # Check image global variable name!



