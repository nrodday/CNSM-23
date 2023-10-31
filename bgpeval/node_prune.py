import os

if __name__ == '__main__':
    result = os.popen('docker node ls --format "{{.ID}} {{.Status}}"| grep Down').read()
    splitted = result.splitlines()
    old_nodes = []
    for line in splitted:
        old_nodes.append(line.split()[0])

    print('Removing the following orphan nodes: ')
    for node in old_nodes:
        print(node)
        os.popen('docker node rm ' + node).read()
    print('Finished removal process, manager should be clean.')