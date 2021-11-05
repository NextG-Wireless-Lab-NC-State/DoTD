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

def static_routing_update_commands(static_routes, links, list_of_Intf_IPs):

    for route in static_routes:
        if len(route) > 2:
            src_node, next_hop_node, dest_node, last_hop_node = route[0], route[1], route[len(route)-1], route[len(route)-2]

            intfs_ips_first_link = get_link_intfs_ips(src_node, next_hop_node, links, list_of_Intf_IPs)
            intfs_ips_last_link  = get_link_intfs_ips(last_hop_node, dest_node, links, list_of_Intf_IPs)

            cmd_on_src_node  = "ip route add "+get_network_address(intfs_ips_last_link[1]["IP"])+"/28 via "+intfs_ips_first_link[1]["IP"]+" dev "+intfs_ips_first_link[0]["Interface"]+" & "
            cmd_on_dest_node = "ip route add "+get_network_address(intfs_ips_first_link[0]["IP"])+"/28 via "+intfs_ips_last_link[0]["IP"]+" dev "+intfs_ips_last_link[1]["Interface"]+" & "
