import topology_extraction
import time
import pickle
from jinja2 import Template
from ipaddress import IPv4Network
import os
import json
import sys

def show_peerings(G):
    peering_relationships = set()
    for edge in G.edges:
        for edge_2 in G.edges:
            if edge[0] == edge_2[1] and edge[1] == edge_2[0]:
                peering_relationships.add(edge)
                #print(edge)
                #print(edge_2)

    #print('# of ASes with Peerings: ', len(peering_relationships))
    #print('ASes with Peerings: ', peering_relationships)
    return peering_relationships

def get_relationships(G):
    node_relationships = {}
    for node in G.nodes:
        customers = []
        providers = []
        peers = []

        for in_edges in G.in_edges(node): # Add all peers
            for out_edges in G.out_edges(node):
                if in_edges[0] == out_edges[1] and in_edges[1] == out_edges[0]:
                    peers.append(in_edges[0])
        for edge in G.in_edges(node):
            if edge[0] not in peers: customers.append(edge[0]) # Add all customers (who are not peers already)
        for edge in G.out_edges(node):
            if edge[1] not in peers: providers.append(edge[1]) # Add all providers (who are not peers already)


        node_relationships[node] = (customers, providers, peers) # Store in dict
        #print("Node: ", node)
        #print("In Edges: ", G.in_edges(node))
        #print("Out Edges: ", G.out_edges(node))

        #print(node_relationships[node])
    return node_relationships


def print_stats(node_relationships):
    tier1=[] #only customers
    tier2=[] #customers + providers + peers
    tier3=[] #only providers
    tier_x=[]
    for node in node_relationships:
        # node:     1234: ([customers], [providers], [peers])
        if node_relationships[node][0] == []: tier3.append(node)
        elif node_relationships[node][0] != [] and node_relationships[node][1] != []: tier2.append(node)
        elif node_relationships[node][1] == []: tier1.append(node)
        else: tier_x.append(node)

    total = len(tier1)+len(tier2)+len(tier3)
    print('Statistics on Node Distribution:')
    print('Tier1', str(len(tier1)) + ' (' + str(100/total*len(tier1)) + '%) ')
    print('Tier2', str(len(tier2)) + ' (' + str(100/total*len(tier2)) + '%) ')
    print('Tier3', str(len(tier3)) + ' (' + str(100/total*len(tier3)) + '%) ')
    print('TierX', len(tier_x))
    print('Total', str(total) + ' (' + str(100/total*total) + '%) ')

def populate_router_ids(node_relationships):
    network = IPv4Network('172.30.0.0/15')
    anounced_network = IPv4Network('10.0.0.0/15')
    reserved_network = IPv4Network('172.30.0.0/24')
    reserved_network_2 = IPv4Network('10.0.0.0/24')
    reserved_ips = {'172.30.0.255'}
    reserved_ips_2 = {'10.0.0.255'}
    router_ids = {}

    router_ids['rpkirtr_server']=['172.30.0.101']

    for node in node_relationships: router_ids[node] = []

    hosts_iterator = (host for host in network.hosts() if host not in reserved_network.hosts() and str(host) not in reserved_ips)
    for node in node_relationships: router_ids[node].append(str(next(hosts_iterator))) #populate dict with ips

    hosts_iterator = (host for host in anounced_network.hosts() if host not in reserved_network_2.hosts() and str(host) not in reserved_ips_2)
    for node in node_relationships: router_ids[node].append(str(next(hosts_iterator))) #populate dict with ips

    return router_ids

def save_router_ids(router_ids, filepath):
    out_file = open(filepath, "w")
    json.dump(router_ids, out_file, indent=6)
    out_file.close()

def build_quagga_configs(node_relationships, router_ids):
    # Build Quagga config files per node
    for node in node_relationships:

        print('')
        print('----------')
        print('')
        print('Node', node)
        print('Node IP', router_ids[node])
        print('Relationships (Cust, Prov, Peer)', node_relationships[node])
        print('')

        neighbors = ''  # fill with content below
        # neighbor 172.37.0.4 remote-as 7674
        # neighbor 172.37.0.4 ebgp-multihop
        # neighbor 172.37.0.4 peer-group upstream
        for customer in node_relationships[node][0]: #create neighbors configs
            neighbors += 'neighbor ' + router_ids[customer][0] + ' remote-as ' + str(customer) + ' \n neighbor ' + router_ids[customer][0] + ' ebgp-multihop \n neighbor ' + router_ids[customer][0] + ' peer-group cust \n '
        for provider in node_relationships[node][1]: #create neighbors configs
            neighbors += 'neighbor ' + router_ids[provider][0] + ' remote-as ' + str(provider) + ' \n neighbor ' + router_ids[provider][0] + ' ebgp-multihop \n neighbor ' + router_ids[provider][0] + ' peer-group upstream \n '
        for peer in node_relationships[node][2]: #create neighbors configs
            neighbors += 'neighbor ' + router_ids[peer][0] + ' remote-as ' + str(peer) + ' \n neighbor ' + router_ids[peer][0] + ' ebgp-multihop \n neighbor ' + router_ids[peer][0] + ' peer-group peer \n '

        #print('Neighbors', neighbors)

        data = {
            "ASN": node,
            "router_id": router_ids[node][0],
            "neighbors": neighbors,
            "local_network": router_ids[node][1] + '/32',
        }

        with open('quagga_config_template.j2') as f:
            template = Template(f.read())
        #print(template.render(data))
        # to save the results
        with open('confd/AS_'+str(node)+'.conf', "w") as fh:
            fh.write(template.render(data))

def build_gobgp_configs(node_relationships, router_ids):
    # Build GoBGP daemon config files per node
    for node in node_relationships:

        print('')
        print('----------')
        print('')
        print('Node', node)
        print('Node IP', router_ids[node])
        print('Relationships (Cust, Prov, Peer)', node_relationships[node])
        print('')

        neighbors = ''  # fill with content below
        #[[neighbors]]
        #  [neighbors.config]
        #    neighbor-address = "172.30.1.0"
        #    peer-as = 1
        for customer in node_relationships[node][0]: #create neighbors configs
            neighbors += '[[neighbors]] \n  [neighbors.config] \n    neighbor-address = "' + router_ids[customer][0] + '"\n    peer-as = ' + str(customer) + '\n' + '  [neighbors.ebgp-multihop.config]\n    enabled = true' + '\n'
        for provider in node_relationships[node][1]: #create neighbors configs
            neighbors += '[[neighbors]] \n  [neighbors.config] \n    neighbor-address = "' + router_ids[provider][0] + '"\n    peer-as = ' + str(provider) + '\n' + '  [neighbors.ebgp-multihop.config]\n    enabled = true' + '\n'
        for peer in node_relationships[node][2]: #create neighbors configs
            neighbors += '[[neighbors]] \n  [neighbors.config] \n    neighbor-address = "' + router_ids[peer][0] + '"\n    peer-as = ' + str(peer) + '\n' + '  [neighbors.ebgp-multihop.config]\n    enabled = true' + '\n'
        print('Neighbors', neighbors)

        data = {
            "ASN": node,
            "router_id": router_ids[node][0],
            "neighbors": neighbors,
            "local_network": router_ids[node][1] + '/32',
        }

        with open('gobgp_config_template.j2') as f:
            template = Template(f.read())
        #print(template.render(data))
        # to save the results
        with open('confd/AS_'+str(node)+'.conf', "w") as fh:
            fh.write(template.render(data))

def build_docker_compose(node_relationships, router_ids):
    data = {
        "nodes": node_relationships,
        "router_id": router_ids
    }

    with open('docker-compose_vm.j2') as f:
        template = Template(f.read())
    # print(template.render(data))
    # to save the results
    with open('confd/docker-compose.yml', "w") as fh:
        fh.write(template.render(data))

def build_srx_config(node_relationships, router_ids):
    data = {
        "nodes": node_relationships,
        "router_id": router_ids
    }

    with open('srx_server.j2') as f:
        template = Template(f.read())
    # print(template.render(data))
    # to save the results
    with open('confd/srx_server.conf', "w") as fh:
        fh.write(template.render(data))

if __name__ == '__main__':
    # Get directional graph with ASes and relationship info
    G = topology_extraction.get_graph("data/1664575200_1664661599.txt", "data/20221001.as-rel2.txt") # Number of nodes the graph should contain in the end
    #G = topology_extraction.get_graph("data/Sample1M_1664575200_1664661599.txt", "data/20221001.as-rel2.txt") # Number of nodes the graph should contain in the end
    #pickle.dump(G, open("data/G_1664575200_1664661599.pickle", "wb"))
    #G = pickle.load(open("data/G_1664575200_1664661599.pickle", "rb"))
    #G = topology_extraction.create_dummy_graph(400) #400 per VM
    print("Loaded Graph")
    #sys.exit()
    #color_map = topology_extraction.get_colormap(G)
    #topology_extraction.draw_graph(G, color_map, "Largest subgraph of directed, connected BGP graph")
    # allocate resources

    #print(len(G.nodes))
    #print(G.nodes)
    #print("")
    #print(G.edges)

    #peering_relationships = show_peerings(G)
    #print('# of ASes with Peerings: ', len(peering_relationships))

    #sys.exit()

    node_relationships = get_relationships(G) # Obtain relationships per node
    print_stats(node_relationships)

    nodes = []
    for node in node_relationships: nodes.append(int(node))
    nodes.sort()
    #print(nodes)
    #print(len(nodes))

    #router_ids = {7672: ['172.30.1.0', '10.0.1.0'], 7673: ['172.30.1.1', '10.0.1.1'], 7674: ['172.30.1.2', '10.0.1.2']}
    router_ids = populate_router_ids(node_relationships)
    save_router_ids(router_ids, "confd/router_ids.json")
    print(router_ids) #


    #Clean-up existing config files
    for i in range(100000):
        if os.path.exists("confd/AS_"+str(i)+".conf"):
            os.remove("confd/AS_"+str(i)+".conf")

    # Build Quagga files
#    build_quagga_configs(node_relationships, router_ids)

    # Build GoBGP files
    build_gobgp_configs(node_relationships, router_ids)

    #Build Docker Compose file
    build_docker_compose(node_relationships, router_ids)

    #Build SRx Server config
    build_srx_config(node_relationships, router_ids)