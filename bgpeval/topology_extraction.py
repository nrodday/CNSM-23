from bgpReader_util import bgp
from datetime import datetime, timedelta
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import multiprocessing as mp
from multiprocessing import Pool, Manager, Process
from functools import partial
import math

import sys
import time
import random
import copy
import numpy as np
import pylab as py
import scipy
import numbers
import pickle
import matplotlib.pylab as pylab
import matplotlib.patches as patches
import multiprocessing as mp

# This suppresses all matplotlib warnings
import warnings
warnings.filterwarnings("ignore")

def readBGPInput(G, filename, providers, customers, peers, as_rel_found, as_rel_notfound):
    bgp_paths = []
    with open(filename, 'r') as f:
        for line in f:
            #if line[:3] == "R|R":
            if bgp.is_relevant_line(line, "R"):
                try:
                    #print(line)
                    as_path = line.split("|")[6].rstrip()
                    as_path = bgp.remove_prepending_from_as_path(as_path)
                    path_len = len(as_path.split(' '))
                    #print(as_path)
                    if "{" in as_path or "}" in as_path: continue
                    #print(as_path)
                    G, as_rel_found, as_rel_notfound = build_graph_per_line(G, as_path, providers, customers, peers, as_rel_found, as_rel_notfound)
                except:
                    continue

    return G, as_rel_found, as_rel_notfound

def readCAIDAInput(filename):
    providers = {}
    customers = {}
    peers = {}

    with open(filename, 'r') as f:
        #   < provider -as > | < customer -as > | -1
        #   < peer -as > | < peer -as > | 0 | < source >

        for line in f:
            #print(line)
            if line.split()[0] == "#": continue #jump over comments
            if line.split("|")[2] == "-1":
                if line.split("|")[0] not in providers:
                    providers[line.split("|")[0]] = []
                providers[line.split("|")[0]].append(line.split("|")[1])

                if line.split("|")[1] not in customers:
                    customers[line.split("|")[1]] = []
                customers[line.split("|")[1]].append(line.split("|")[0])

            elif line.split("|")[2] == "0":
                if line.split("|")[0] not in peers:
                    peers[line.split("|")[0]] = []
                peers[line.split("|")[0]].append(line.split("|")[1])

                if line.split("|")[1] not in peers:
                    peers[line.split("|")[1]] = []
                peers[line.split("|")[1]].append(line.split("|")[0])

    #print(customers)

    return providers, customers, peers

def get_relationship(former_as, latter_as, providers, customers, peers):
    #   < provider -as > | < customer -as > | -1
    #   < peer -as > | < peer -as > | 0 | < source >

    if former_as in providers:
        if latter_as in providers[former_as]: return "provider"

    elif former_as in customers:
        if latter_as in customers[former_as]: return "customer"

    elif former_as in peers:
        if latter_as in peers[former_as]: return "peer"

    return False

def build_graph_per_line(G, as_path, providers, customers, peers, as_rel_found, as_rel_notfound):
    for position in range(0,len(as_path.split(" "))):
        as_number = as_path.split(" ")[position]
        G.add_node(as_number)

        #add edges from second position starting
        if position != 0:
            #print(as_path.split(" ")[position-1],as_path.split(" ")[position])
            former_as = as_path.split(" ")[position - 1]
            latter_as = as_path.split(" ")[position]
            #print()
            relationsship = get_relationship(former_as, latter_as, providers, customers, peers)
            #print(relationsship)

            #Counter
            if relationsship == False: as_rel_notfound += 1
            else: as_rel_found += 1

            if relationsship == False:
                #print("AS could not be found in CAIDA dataset, fallback to bidirectional")
                #G.add_edge(former_as, latter_as)
                #G.add_edge(latter_as, former_as)
                pass
            elif relationsship == "customer": G.add_edge(former_as, latter_as)
            elif relationsship == "provider": G.add_edge(latter_as, former_as)
            elif relationsship == "peer":
                G.add_edge(former_as, latter_as)
                G.add_edge(latter_as, former_as)

    return G, as_rel_found, as_rel_notfound


def print_graph_stats(G, as_rel_found, as_rel_notfound):
    print()
    print("Nodes of graph with isolates: ", len(G.nodes()))
    # print(G.nodes())

    print("Removing " + str(len(list(nx.isolates(G)))) + " isolates")
    G.remove_nodes_from(list(nx.isolates(G)))

    print("Nodes of graph without isolates: ", len(G.nodes()))
    # print(G.nodes())

    print()
    print("Edges of graph: ", len(G.edges()))
    # print(G.edges())

    print()
    print("AS Rel dataset stats: ")
    print("Found relationships: ", as_rel_found)
    print("Not found relationships: ", as_rel_notfound)

    # This section collects nodes that have no outgoing edges
    tier1 = set()
    for node in G.nodes():
        if not G.out_edges(node):
            tier1.add(node)
        # print(len(G.out_edges(node)))

    # print(G.out_degree())

    # This section builds a dict with the degree as the key and the ASs as values
    stats = {}
    for k, v in G.out_degree():
        # print(k, v)
        if v in stats:
            stats[v].append(k)
        else:
            stats[v] = []
            stats[v].append(k)

    # print(stats)
    # print()
    # print("Out degree | ","# ASs")
    # for k,v in sorted(stats.items()):
    #    print(k, len(v))



def get_colormap(G):

    if nx.is_directed(G):
        #Generate color map to color nodes according to out_degree
        print()
        print("Creating color map")
        color_map = []
        for node in G.nodes():
            if G.out_degree(node) == 0: color_map.append('r')
            elif G.out_degree(node) == 1: color_map.append('y')
            elif G.out_degree(node) == 2: color_map.append('g')
            elif 2 < G.out_degree(node) <= 15: color_map.append('b')
            elif G.out_degree(node) > 15: color_map.append('grey')
        print("Finished color map")
    else:
        #Generate color map to color nodes according to out_degree
        print()
        print("Creating color map")
        color_map = []
        for node in G.nodes():
            if G.degree(node) == 0: color_map.append('r')
            elif G.degree(node) == 1: color_map.append('y')
            elif G.degree(node) == 2: color_map.append('g')
            elif 2 < G.degree(node) <= 15: color_map.append('b')
            elif G.degree(node) > 15: color_map.append('grey')
        print("Finished color map")

    return color_map

def graph_sample_with_KS_test(G, S, algorithm, size):
    abstraction_G = graph_sampling(S, algorithm, size)
    if abstraction_G == None:
        kstest_result = {}
        kstest_result[0] = 1.0  # statistic
        kstest_result[1] = 0.0  # pvalue
    else:
        # print("Reduced Original is connected: ", nx.is_connected(S_new))
        # print("Sampled is connected: ", nx.is_connected(abstraction_G))

        # 5. Obtain final abstracted directed graph (delete nodes not present in the sampled graph from original)
        # print()
        # print("5. Obtain final abstracted directed graph (delete nodes not present in the sampled graph from original)")

        sampled_G = get_sampled_G(G, abstraction_G)
        kstest_result = perform_kstest(G, sampled_G)
        print("Sample #: " + str(size) + " - KS Test different: ", kstest_result)

    return kstest_result

def graph_sampling(S, algorithm, size):
    ###################################################################
    ###  Choose an algorithm that selects nodes that are connected!  ##
    ###################################################################
    working_graph = False #Bug in the library, crashed for some seed values
    failed_Seed_counter = 0
    while working_graph != True:
        if failed_Seed_counter > 100:
            new_graph = None
            break #Break if we could not find a working sample after 1k tries
        try:

            seed_value = random.randint(1,2147483646) #To obtain different graph each time

            #B = nx.complete_graph(1000)
            if algorithm == "RandomWalk":
                #print("RandomWalk")
                sampler = RandomWalkSampler(size, seed=seed_value)
            elif algorithm == "ForestFire":
                #print("ForestFire")
                sampler = ForestFireSampler(size, seed=seed_value)
            elif algorithm == "SnowBall":
                #print("Snowball")
                sampler = SnowBallSampler(size, seed=seed_value)


            # sampler = PageRankBasedSampler(size)
            new_graph = sampler.sample(S)

            #print("Successful seed: ", seed_value)
            working_graph = True
        except:
            failed_Seed_counter += 1
            pass

    print("Failed seeds: ", failed_Seed_counter)

    return new_graph


def draw_graph(G, color_map=[], title="graph"):
    print()
    print("Number of nodes: " + str(len(G.nodes())) + " ; Number of color_map items: " + str(len(color_map)))
    print("Drawing graph...")

    if len(color_map) != 0:
        nx.draw(G, node_size=4, with_labels=False, node_color=color_map, width=0.2, arrowsize=2)
    else:
        nx.draw(G, node_size=4, with_labels=False, width=0.2, arrowsize=2)

    #plt.savefig("graph.pdf")
    plt.figure(figsize=(12,12))
    plt.show()  # display

def transform_graph_to_consecutive_integers(S, nodes_indices_translation, recursive=False):
    nodes = sorted([int(i) for i in S.nodes])  # get nodes as int
    S_new = nx.Graph()
    index = 0
    for node in nodes:
        if not recursive == True:
            nodes_indices_translation[index] = node
            S_new.add_node(index, label=node)
        else:
            nodes_indices_translation[index] = S.nodes[node]['label']
            S_new.add_node(index, label=S.nodes[node]['label'])
        index += 1


    edges = S.edges
    print("# Edges", len(edges))
    # print(edges)

    tmp_tumple = (0, 0)
    new_edges = []
    for edge in edges:
        for key, value in nodes_indices_translation.items():
            if int(edge[0]) == value:
                tmp_tumple = (key, 0)
                # print("Swapped: " + str(edge) + " for " + str(tmp_tumple))
                break

        for key, value in nodes_indices_translation.items():
            if int(edge[1]) == value:
                tmp_tumple = (tmp_tumple[0], key)
                # print("Swapped: " + str(edge) + " for " + str(tmp_tumple))
                break

        new_edges.append(tmp_tumple)

    print()
    # print("Length", len(new_edges))
    # print(new_edges)
    S_new.add_edges_from(new_edges)

    return S_new, nodes_indices_translation


def qqplot(x, y, quantiles=None, interpolation='nearest', ax=None, rug=False,
           rug_length=0.05, rug_kwargs=None, title="QQPlot", **kwargs):
    """Draw a quantile-quantile plot for `x` versus `y`.

    Parameters
    ----------
    x, y : array-like
        One-dimensional numeric arrays.

    ax : matplotlib.axes.Axes, optional
        Axes on which to plot. If not provided, the current axes will be used.

    quantiles : int or array-like, optional
        Quantiles to include in the plot. This can be an array of quantiles, in
        which case only the specified quantiles of `x` and `y` will be plotted.
        If this is an int `n`, then the quantiles will be `n` evenly spaced
        points between 0 and 1. If this is None, then `min(len(x), len(y))`
        evenly spaced quantiles between 0 and 1 will be computed.

    interpolation : {‘linear’, ‘lower’, ‘higher’, ‘midpoint’, ‘nearest’}
        Specify the interpolation method used to find quantiles when `quantiles`
        is an int or None. See the documentation for numpy.quantile().

    rug : bool, optional
        If True, draw a rug plot representing both samples on the horizontal and
        vertical axes. If False, no rug plot is drawn.

    rug_length : float in [0, 1], optional
        Specifies the length of the rug plot lines as a fraction of the total
        vertical or horizontal length.

    rug_kwargs : dict of keyword arguments
        Keyword arguments to pass to matplotlib.axes.Axes.axvline() and
        matplotlib.axes.Axes.axhline() when drawing rug plots.

    title : basestring
        Title of plot

    kwargs : dict of keyword arguments
        Keyword arguments to pass to matplotlib.axes.Axes.scatter() when drawing
        the q-q plot.
    """
    plt.figure()

    # Get current axes if none are provided
    if ax is None:
        ax = plt.gca()

    if quantiles is None:
        quantiles = min(len(x), len(y))

    # Compute quantiles of the two samples
    if isinstance(quantiles, numbers.Integral):
        quantiles = np.linspace(start=0, stop=1, num=int(quantiles))
    else:
        quantiles = np.atleast_1d(np.sort(quantiles))
    x_quantiles = np.quantile(x, quantiles, interpolation=interpolation)
    y_quantiles = np.quantile(y, quantiles, interpolation=interpolation)

    # Draw the rug plots if requested
    if rug:
        # Default rug plot settings
        rug_x_params = dict(ymin=0, ymax=rug_length, c='gray', alpha=0.5)
        rug_y_params = dict(xmin=0, xmax=rug_length, c='gray', alpha=0.5)

        # Override default setting by any user-specified settings
        if rug_kwargs is not None:
            rug_x_params.update(rug_kwargs)
            rug_y_params.update(rug_kwargs)

        # Draw the rug plots
        for point in x:
            ax.axvline(point, **rug_x_params)
        for point in y:
            ax.axhline(point, **rug_y_params)

    # Draw the q-q plot
    ax.scatter(x_quantiles, y_quantiles, **kwargs)
    y_lim = plt.ylim()
    x_lim = plt.xlim()
    plt.plot(x_lim, y_lim, 'k-', color='r')

    plt.xlabel('Original')
    plt.ylabel('Sample')
    plt.title(title + str(len(quantiles)))
    plt.show()
    plt.close()

def get_connected_G(G,largest_subgraph_undirected_G):
    # Get all nodes that are present in abstraction
    remaining_nodes = []
    [remaining_nodes.append(str(node)) for node in largest_subgraph_undirected_G.nodes]

    print("# Original nodes:", len(G.nodes))
    print("# Remaining nodes:",len(remaining_nodes))

    deleted_nodes = G.nodes - remaining_nodes
    copied_G = copy.deepcopy(G)
    copied_G.remove_nodes_from(deleted_nodes)  # Remove all nodes that are not present in the sampled graph

    return copied_G

def perform_kstest(G,sampled_G):
    pr_original = nx.pagerank(G, alpha=0.85)
    pr_sample = nx.pagerank(sampled_G, alpha=0.85)

    np_pr_original = np.sort(np.fromiter(pr_original.values(), dtype=float))  # To numpy arrays
    np.set_printoptions(precision=20)

    np_pr_sample = np.sort(np.fromiter(pr_sample.values(), dtype=float))
    np.set_printoptions(precision=20)

    kstest_result = scipy.stats.ks_2samp(np_pr_original, np_pr_sample)

    return kstest_result

def create_cdf(np_pr_original, np_pr_sample):
    #y_original = np.arange(1,len(np_pr_original)+1 / len(np_pr_original)) # For absolute y-axis
    y_original = np.arange(0,1, 1/ len(np_pr_original)) #For relative y-axis
    y_sample = np.arange(0,1, 1 / len(np_pr_sample))
    #print(len(y_sample))
    #print(y_sample)
    plt.clf()
    plt.plot(np_pr_original, y_original, marker=".", linestyle="none", color="g")
    plt.plot(np_pr_sample, y_sample, marker="+", linestyle="none", color="r")
    plt.xlabel("Metric Value")
    plt.ylabel("Relative Frequency")
    plt.margins(0.02)
    plt.title("CDF")
    plt.show()

def plot_find_min_sample_size(G, S_new, algorithm): #This function creates a plot that shows when the p value is high enough. We found the right sample size.

    p_values = []
    print(len(S_new.nodes()))
    sizes = []
    #[sizes.append(i) for i in range(1,len(S_new.nodes()))] #for each size from graph
    [sizes.append(i) for i in range(1, 3800)] #for sizes until x
    with Pool(processes=112) as p:
        m = mp.Manager()
        func = partial(graph_sample_with_KS_test, G, S_new, algorithm)
        results = p.map(func, sizes)
        #clean up once all tasks are done
        p.close()
        p.join()

    #print(results)
    for result in results:
        p_values.append(result[1]) #Write to list

    return p_values


def plot_minimum_sample_sizes(G, S_new):

    p_values_randomwalk = plot_find_min_sample_size(G, S_new, algorithm="RandomWalk") #Creates a plot that shows which is the best value for sample size
    #plot_find_min_sample_size(G, S_new, algorithm="ForestFire")  # Creates a plot that shows which is the best value for sample size
    p_values_snowball = plot_find_min_sample_size(G, S_new, algorithm="SnowBall")

    #Save values for later plotting
    #pickle.dump(p_values_randomwalk, open("p_values_randomwalk.p", "wb"))
    #pickle.dump(p_values_snowball, open("p_values_snowball.p", "wb"))
    #p_values_randomwalk = pickle.load(open("p_values_randomwalk.p", "rb"))
    #p_values_snowball = pickle.load(open("p_values_snowball.p", "rb"))

    #Print plot

    plt.plot(p_values_randomwalk,color='red', marker="+", label='RandomWalk')
    plt.plot(p_values_snowball,color='blue', label='Snowball')
    plt.ylabel('p values')
    plt.xlabel('sample size')
    plt.legend(loc="lower right")
    plt.title('Find sample size value for: RandomWalk & Snowball')
    plt.xticks((0,950,1900,2850,3800), (0,25,50,75,100))
    #plt.axvline(x=1900, linewidth=2, color='grey')
    #plt.axvline(x=2850, linewidth=2, color='grey')
    rect = patches.Rectangle((1900, -0.1), 950, 1.2, linewidth=2, edgecolor='grey', facecolor='none', hatch='/') #Create patch
    ax.add_patch(rect)    # Add the patch to the Axes
    plt.show()
    #plt.savefig('abstraction_size.pdf')

def hirarchical_sampling(G, S_new, algorithm):
    print("Input nodes: ", len(S_new.nodes))
    abstraction_G = graph_sampling(S_new, round(len(S_new.nodes)/100*20,0), algorithm=algorithm) #sample size: 50%

    sampled_G = get_sampled_G(G, abstraction_G)
    kstest_result = perform_kstest(G, sampled_G)

    print()
    #print("Reduced Original is connected: ", nx.is_connected(S_new))
    print("Original Is directed: ", nx.is_directed(G))
    print("Original graph length edges", len(G.edges))
    print("Original graph # nodes: ", len(G.nodes()))
    print()
    #print("Sample is connected: ", nx.is_connected(sampled_G))
    print("Sample Is directed: ", nx.is_directed(sampled_G))
    print("Sample graph length edges", len(sampled_G.edges))
    print("Sample graph # nodes: ", len(sampled_G.nodes()))
    print()
    print(kstest_result)
    print()
    print("----------------------------------------------")
    print()

    S_new_2, nodes_indices_translation = transform_graph_to_consecutive_integers(S, nodes_indices_translation)
    sampler = RandomWalkSampler(200, seed=3474)
    abstraction_G_2 = sampler.sample(abstraction_G)

    if not len(abstraction_G.nodes) < 4000:
        hirarchical_sampling(G, abstraction_G, algorithm)

def get_graph(filename, caida_as_rel_dataset):
    start = time.time()
    #as_paths = readBGPInput("data/1601258400_1601261999.txt")

    #print(as_paths)

    # 1. Build initial directed graph
    print()
    print("1. Build initial directed graph")
    G = nx.DiGraph()
    print("Started reading CAIDA file", time.time())
    providers, customers, peers = readCAIDAInput(caida_as_rel_dataset)
    as_rel_found, as_rel_notfound = 0, 0
    print("Finished reading CAIDA file", time.time())
    print("Started reading input file, line by line", time.time())
    G, as_rel_found, as_rel_notfound = readBGPInput(G, filename, providers, customers, peers, as_rel_found, as_rel_notfound)
    print("Finished reading input file, line by line", time.time())
    print_graph_stats(G, as_rel_found, as_rel_notfound)
    #pickle.dump(G, open("data/G.pickle", "wb"))
    #G = pickle.load(open("data/G.pickle", "rb"))
    #color_map = get_colormap(G)
    #draw_graph(G, color_map, "Initial, directed graph")
    print("Is directed: ", nx.is_directed(G))
    print("Original graph length edges", len(G.edges))
    print("Original graph # nodes: ", len(G.nodes()))

    # 2. Transform graph into undirected representation
    print()
    print("2. Transform graph into undirected representation")
    undirected_G = G.to_undirected(False, True)
    print("Is directed: ", nx.is_directed(undirected_G))
    print("Is connected: ", nx.is_connected(undirected_G))
    print("Undirected graph length edges", len(undirected_G.edges))
    print("Undirected graph # nodes: ", len(undirected_G.nodes()))
    #draw_graph(undirected_G, get_colormap(undirected_G), "Undirected graph")


    # 3. Only select largest subgraph within the whole graph (such that everything is connected)
    print()
    print("3. Only select largest subgraph within the whole graph (such that everything is connected)")
    S = undirected_G.subgraph(sorted(nx.connected_components(undirected_G), key=len, reverse=True)[0]).copy()
    #pickle.dump(S, open("data/S.pickle", "wb"))
    #S = pickle.load(open("data/S.pickle", "rb"))
    #[print(len(c)) for c in sorted(nx.connected_components(undirected_G), key=len, reverse=True)] #This prints the length of all existing subgraphs
    print("Is directed: ", nx.is_directed(S))
    print("Is connected: ", nx.is_connected(S))
    print("Subgraph length edges: ", len(S.edges))
    print("Subgraph # nodes: ", len(S.nodes()))
    #draw_graph(S, get_colormap(S), "Largest subgraph")


    # 4. Revert to directed graph
    print()
    print("4. Revert to directed graph")
    directed_connected_G = get_connected_G(G, S)
    print("Is directed: ", nx.is_directed(directed_connected_G))
    print("Subgraph length edges: ", len(directed_connected_G.edges))
    print("Subgraph # nodes: ", len(directed_connected_G.nodes()))
    #draw_graph(directed_connected_G, get_colormap(directed_connected_G), "Largest subgraph of directed, connected BGP graph")

    end = time.time()
    print()
    print("Time seconds: ", end - start)
    print("Time minutes: ", (end - start) / 60)

    return directed_connected_G


def create_dummy_graph(size):
    size = size - 4
    G = nx.DiGraph()

    G.add_node(1)
    G.add_node(2)
    G.add_node(3)
    G.add_node(4)
    G.add_node(5)
    G.add_node(6)

    G.add_edge(3, 1) #cust, prov
    G.add_edge(4, 1) #cust, prov
    G.add_edge(4, 2) #cust, prov
    G.add_edge(4, 3) #peer
    G.add_edge(3, 4) #peer
    G.add_edge(5, 4) #peer
    G.add_edge(4, 5) #peer
    G.add_edge(6, 4) #cust, prov

# This section spawns as many as 250 child nodes per parent. The parent is added to the AS6.
    counter = 0
    parent = 0
    for x in range(7,size+7):
        if counter == 0:
            parent = x
            G.add_node(parent)
            G.add_edge(parent, 6)  # cust, prov
        else:
            G.add_node(x)
            G.add_edge(x, parent)  # cust, prov

        counter += 1
        if counter == 250: #max number of cust per provider node to not DDOS Quagga
            counter = 0





    return G