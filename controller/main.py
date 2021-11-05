from mininet.net import Mininet
from mininet.node import Node, OVSKernelSwitch, Controller, RemoteController
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.link import *
from mininet.topo import Topo
from mininet.log import setLogLevel, info
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
sys.path.append("../")
from mobility.read_real_tles import *
from mobility.mobility_utils import *
from mobility.read_gs import *
from mininet_infra.create_mininet_topology import *
from routing.routing_utils import *

def controller_thread(links):
    available_ips = generate_ips_for_constellation()
    list_of_Intf_IPs = assign_ips_for_constellation(links, available_ips)
    # for ip in list_of_Intf_IPs:
    #     print ip

def main():
    N = 3

    satellites = load.tle_file("https://celestrak.com/NORAD/elements/starlink.txt")
    satellites_by_name = {sat.name: sat for sat in satellites}
    planes = extract_planes("../mobility/starlink_tles.txt")

    cur_planes = planes["Planes"]
    print len(planes["Unassigned"])
    ts = load.timescale()
    t = ts.now()

    sorted_planes = sort_satellites_within_plane(cur_planes, satellites_by_name, t)

    available_satellites = []
    for key in sorted_planes.keys():
        sats = ""
        for satellite in sorted_planes[key]:
            sats += str(satellites_by_name[str(satellite)].name).split("-")[1]+","
            available_satellites.append(satellites_by_name[str(satellite)])

    available_satellites_by_name = {sat.name: sat for sat in available_satellites}
    # print available_satellites[0]
    actual_sat_number_to_counter = label_satellites_properly(sorted_planes, len(available_satellites_by_name))

    ground_stations = read_gs("../mobility/ground_stations.txt")

    num_of_satellites = len(available_satellites_by_name)
    num_of_ground_stations = len(ground_stations)

    print num_of_satellites, num_of_ground_stations
    conn_mat_size = num_of_satellites + num_of_ground_stations

    connectivity_matrix = [[0 for c in range(conn_mat_size)] for r in range(conn_mat_size)]
    connectivity_matrix = mininet_add_ISLs(connectivity_matrix, available_satellites_by_name, actual_sat_number_to_counter, sorted_planes, 0, 0, "SAME_ORBIT_AND_BASED_ON_DISTANCE_FOR_INTER_ORBIT", t)
    connectivity_matrix = mininet_add_GSLs(connectivity_matrix, available_satellites_by_name, actual_sat_number_to_counter, ground_stations, t, 12, "BASED_ON_DISTANCE_ONLY_MININET")

    # available_ips = generate_ips_for_constellation()

    ############## For test purposes
    # G = nx.Graph()
    # for sat in available_satellites_by_name:
    #     G.add_node(sat)
    #
    # G = graph_add_ISLs(G, available_satellites_by_name, sorted_planes, 0, 0, "SAME_ORBIT_AND_BASED_ON_DISTANCE_FOR_INTER_ORBIT", t)
    # for edge in G.edges():
    #     print edge
    ##############

    topology = sat_network(N=N)
    topg = topology.create_sat_network(satellites=available_satellites_by_name, ground_stations=ground_stations, connectivity_matrix=connectivity_matrix)

    x = threading.Thread(target=controller_thread, args=(topg["links"],))
    # x.start()
    net = Mininet(topo = topology, link=TCLink, autoSetMacs = True)
    net.start()
    x.start()
    CLI( net)
    net.stop()
    #
    # os.system("killall -9 ospfd zebra")
    # os.system("rm -f /tmp/*.pid")

setLogLevel('info')    # 'info' is normal; 'debug' is for when there are problems
main()
