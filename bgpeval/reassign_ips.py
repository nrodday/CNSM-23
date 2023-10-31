import json
import os
import subprocess



if __name__ == '__main__':
    io = open("confd/router_ids.json", "r")
    router_ids = json.load(io)

    #os.system('docker ps --format "{{.Names}}"')
    test = os.popen('docker ps --format "{{.Names}}"').read()
    splitted = test.splitlines()
    for s in splitted:
        print(s)
        start = 'nist-bgp_'
        end = '.1.'
        extracted_part = (s[s.find(start) + len(start):s.rfind(end)])
        if extracted_part.replace('AS_', '').isnumeric() or extracted_part=='rpkirtr_server':
            if extracted_part.replace('AS_', '').isnumeric(): extracted_part = extracted_part.replace('AS_', '')
            ip = router_ids[extracted_part][0]
            command = 'docker network disconnect bgp_net ' + s
            #command = 'ls -la'
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
            process.wait()
            if process.returncode == 0:
                print('Disconnect successful')
                command = 'docker network connect --ip '+ip+' bgp_net ' + s
                # command = 'ls -la'
                process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
                process.wait()
                if process.returncode == 0:
                    print('Reconnect successful')
                else: print('Reconnect UNsuccessful')
            else: print('Disconnect UNsuccessful')