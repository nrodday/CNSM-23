import json
import os
import subprocess
from re import search
import time
from multiprocessing import Pool

def prune_configs(s):
    command = 'docker config rm ' + s
    # command = 'ls -la'
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
    process.wait()
    if process.returncode == 0:
        print('Removed config for ' + s)
    else:
        print('ERROR removing config for ' + s)
    time.sleep(1)

def prune_services(s):
    command = 'docker service rm ' + s
    # command = 'ls -la'
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
    process.wait()
    if process.returncode == 0:
        print('Removed service ' + s)
    else:
        print('ERROR removing service ' + s)
    time.sleep(2)

if __name__ == '__main__':

    result = os.popen('docker service ls --format "{{.Name}}"').read()
    splitted = result.splitlines()

    print('Started removing services')
    with Pool(400) as p:
        p.map(prune_services, splitted)
    print('Finished removing services')

#    result = os.popen('docker config ls --format "{{.Name}}"').read()
#    splitted = result.splitlines()

    print('Started removing configs')
    with Pool(400) as p:
        p.map(prune_configs, splitted)
    print('Finished removing configs')