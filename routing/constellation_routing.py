import argparse
import re
import time
import os
import numpy as np
import datetime

import threading
import Queue
from copy import copy, deepcopy

import networkx as nx
import matplotlib.pyplot as plt
import bellmanford as bf
import itertools
from multiprocessing import Process, Manager, Pool

import sys
sys.path.append("./")
from routing.routing_utils import *

def static_routing_worker(args):
    (
        G,
        p,
        q
    ) = args

    new_path = []
    path_length, path_nodes, negative_cycle = bf.bellman_ford(G, source=p, target=q, weight="weight")
    new_path.append(path_nodes)

    return new_path

def initial_routing(satellites, ground_stations, connectivity_matrix):
    mega_constellation_graph = nx.Graph()
    for n in range(len(satellites)+len(ground_stations)):
        mega_constellation_graph.add_node(n)        # nodes where n > len(satellites) are ground stations

    for i in range(len(connectivity_matrix)):
        for j in range(len(connectivity_matrix[i])):
            if connectivity_matrix[i][j] == 1:
                # print i, j
                mega_constellation_graph.add_edge(i, j, weight=1)

    static_routing_list_args = []
    print len(mega_constellation_graph.edges())
    for p in range(len(satellites)+len(ground_stations)):#
        for q in range(len(satellites)+len(ground_stations)):
            static_routing_list_args.append((mega_constellation_graph, p, q))

    pool = Pool(70)
    static_routes = pool.map(static_routing_worker, static_routing_list_args)
    pool.close()
    pool.join()

    return static_routes

def static_routing_worker(args):
    (
        Gr,
        source,
        destination
    ) = args

    new_path = []
    path_length, path_nodes, negative_cycle = bf.bellman_ford(Gr, source=source, target=destination, weight="weight")
    new_path.append(path_nodes)

    return new_path

def static_routing(G, destinations, num_of_satellites, num_of_ground_stations, num_of_threads):
    for i in range(num_of_satellites+num_of_ground_stations):
        for dest in destinations:
            destination = -1
            if "gs" in dest[0]:
                destination = int(dest[0][2:])+num_of_satellites
            elif "sat" in dest[0]:
                destination = int(dest[0][3:])

            list_args.append((G, i, destination))

    pool = Pool(num_of_threads)
    static_routes = pool.map(static_routing_worker, list_args)
    pool.close()
    pool.join()

    return static_routes

def static_routing_update_commands(static_routes, links, list_of_Intf_IPs, satellites):
    for route in static_routes:
        current_route = route[0];
        if len(current_route) > 2:
            src_node, next_hop_node, dest_node, last_hop_node = current_route[0], current_route[1], current_route[len(current_route)-1], current_route[len(current_route)-2]

            src_node = "sat"+str(src_node) if src_node < len(satellites) else "gs"+str(src_node%len(satellites))
            next_hop_node = "sat"+str(next_hop_node) if next_hop_node < len(satellites) else "gs"+str(next_hop_node%len(satellites))
            dest_node = "sat"+str(dest_node) if dest_node < len(satellites) else "gs"+str(dest_node%len(satellites))
            last_hop_node = "sat"+str(last_hop_node) if last_hop_node < len(satellites) else "gs"+str(last_hop_node%len(satellites))

            src_node_intf = ""
            dest_node_intf= ""
            next_h_node_intf = ""
            last_h_node_intf = ""

            for link in links:
                if str(src_node)+str("-") in link and str(next_hop_node)+str("-") in link:
                    intfs = link.split(":")
                    if str(src_node) in intfs[0] and str(next_hop_node) in intfs[1]:
                        src_node_intf = intfs[0]
                        next_h_node_intf = intfs[1]
                    elif str(src_node) in intfs[1] and str(next_hop_node) in intfs[0]:
                        src_node_intf = intfs[1]
                        next_h_node_intf = intfs[0]

                if str(dest_node)+str("-") in link and str(last_hop_node)+str("-") in link:
                    intfs = link.split(":")
                    if str(dest_node) in intfs[0] and str(last_hop_node) in intfs[1]:
                        dest_node_intf = intfs[0]
                        last_h_node_intf = intfs[1]
                    elif str(dest_node) in intfs[1] and str(last_hop_node) in intfs[0]:
                        dest_node_intf = intfs[1]
                        last_h_node_intf = intfs[0]

            if dest_node_intf != "" and next_h_node_intf != "" and src_node_intf !="":
                cmd_on_src_node  = "ip route add "+get_network_address(get_node_intf_ip(dest_node_intf, list_of_Intf_IPs))+"/28 via "+get_node_intf_ip(next_h_node_intf, list_of_Intf_IPs)+" dev "+src_node_intf
                print cmd_on_src_node

            if src_node_intf != "" and last_h_node_intf != "" and dest_node_intf != "":
                cmd_on_dest_node = "ip route add "+get_network_address(get_node_intf_ip(src_node_intf, list_of_Intf_IPs))+"/28 via "+get_node_intf_ip(last_h_node_intf, list_of_Intf_IPs)+" dev "+dest_node_intf
                print cmd_on_dest_node


def get_static_route_parameter(route, links, list_of_Intf_IPs, satellites):
    parameters = []
    current_route = route[0];
    if len(current_route) > 2:
        # print current_route
        src_node, next_hop_node, dest_node, last_hop_node = current_route[0], current_route[1], current_route[len(current_route)-1], current_route[len(current_route)-2]

        src_node = "sat"+str(src_node) if src_node < len(satellites) else "gs"+str(src_node%len(satellites))
        next_hop_node = "sat"+str(next_hop_node) if next_hop_node < len(satellites) else "gs"+str(next_hop_node%len(satellites))
        dest_node = "sat"+str(dest_node) if dest_node < len(satellites) else "gs"+str(dest_node%len(satellites))
        last_hop_node = "sat"+str(last_hop_node) if last_hop_node < len(satellites) else "gs"+str(last_hop_node%len(satellites))

        # print src_node, next_hop_node, dest_node, last_hop_node
        src_node_intf = ""
        dest_node_intf= ""
        next_h_node_intf = ""
        last_h_node_intf = ""

        for link in links:
            if str(src_node)+str("-") in link and str(next_hop_node)+str("-") in link:
                intfs = link.split(":")
                if str(src_node) in intfs[0] and str(next_hop_node) in intfs[1]:
                    src_node_intf = intfs[0]
                    next_h_node_intf = intfs[1]
                elif str(src_node) in intfs[1] and str(next_hop_node) in intfs[0]:
                    src_node_intf = intfs[1]
                    next_h_node_intf = intfs[0]

            if str(dest_node)+str("-") in link and str(last_hop_node)+str("-") in link:
                intfs = link.split(":")
                if str(dest_node) in intfs[0] and str(last_hop_node) in intfs[1]:
                    dest_node_intf = intfs[0]
                    last_h_node_intf = intfs[1]
                elif str(dest_node) in intfs[1] and str(last_hop_node) in intfs[0]:
                    dest_node_intf = intfs[1]
                    last_h_node_intf = intfs[0]

        # print dest_node_intf
        if dest_node_intf != "":
            dest_nw_ip = get_network_address(get_node_intf_ip(dest_node_intf, list_of_Intf_IPs))+"/28"
            next_hop_ip = get_node_intf_ip(next_h_node_intf, list_of_Intf_IPs)
            out_interface = src_node_intf
        else:
            print "Error: No link between ", str(last_hop_node), " and ", str(dest_node)
            exit()

        if src_node_intf != "":
            src_nw_ip = get_network_address(get_node_intf_ip(src_node_intf, list_of_Intf_IPs))+"/28"
            last_hop_ip = get_node_intf_ip(last_h_node_intf, list_of_Intf_IPs)
            out_interface_2 = dest_node_intf
        else:
            print "Error: No link between ", str(src_node), " and ", str(next_hop_node)
            exit()

        parameters.append(src_node)
        parameters.append(dest_nw_ip)
        parameters.append(next_hop_ip)
        parameters.append(out_interface)

        parameters.append(dest_node)
        parameters.append(src_nw_ip)
        parameters.append(last_hop_ip)
        parameters.append(out_interface_2)

    return parameters
