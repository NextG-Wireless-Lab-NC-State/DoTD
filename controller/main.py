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

import socket
import time
import subprocess
import threading

import sys
sys.path.append("../")
from mobility.read_real_tles import *
from mobility.mobility_utils import *
from mobility.read_gs import *
from mininet_infra.create_mininet_topology import *
from routing.routing_utils import *
from routing.constellation_routing import *
from comm_protocol.controller_main import *

def log_info_for_controller(current_time, links, m_intfs):
    links_log = open("links_log.txt", "w")
    links_log.write(current_time + "\n")
    for link in links:
        links_log.write(link + "\n")
    links_log.close()

    m_intf_log = open("m_intf_log.txt", "w")
    for intf in m_intfs:
        m_intf_log.write(intf["node"] + "\t" + intf["mgnt_ip"] + "\n")
    m_intf_log.close()

    print("..... Logged!\n")

def main():
    N = 3

    satellites = load.tle_file("https://celestrak.com/NORAD/elements/starlink.txt")
    satellites_by_name = {sat.name: sat for sat in satellites}
    planes = extract_planes("../mobility/starlink_tles.txt")

    cur_planes = planes["Planes"]
    print len(planes["Unassigned"])
    ts = load.timescale()
    t = ts.now()
    print t
    sorted_planes = sort_satellites_within_plane(cur_planes, satellites_by_name, t)

    # Get the satellites in planes only, igonore the Unassigned satellites
    available_satellites = []
    for key in sorted_planes.keys():
        sats = ""
        for satellite in sorted_planes[key]:
            sats += str(satellites_by_name[str(satellite)].name).split("-")[1]+","
            available_satellites.append(satellites_by_name[str(satellite)])

    available_satellites_by_name = {sat.name: sat for sat in available_satellites}

    # convert satellite names from STARLINK-xxxx to just a number
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
    initial_routes = initial_routing(available_satellites_by_name, ground_stations, connectivity_matrix)
    for route in initial_routes:
        print route
    topology = sat_network(N=N)
    topg = topology.create_sat_network(satellites=available_satellites_by_name, ground_stations=ground_stations, connectivity_matrix=connectivity_matrix)
    # log_info_for_controller(t.utc_strftime(), topg["links"], topg["management_interface"]);
    net = Mininet(topo = topology, link=TCLink, autoSetMacs = True)
    net.start()
    # topology.initial_ipv4_assignment_for_interfaces(net, available_ips)
    # print len(connectivity_matrix)

    # for route in initial_routes:
    #     print route
    # topology.startListener(net, available_satellites_by_name, ground_stations, topg["management_interface"])
    CLI( net)
    # UDPSocket = socket(family=AF_INET, type=SOCK_DGRAM)
    # UDPSocket.bind(("", 20001))
    # print "Mininet main listener is created ... "
    # while(True):
    #     bytesAddressPair = UDPSocket.recvfrom(1024)
    #     print bytesAddressPair
    #     recv_msg = updateTopologyMsg.c_m_update_topology()
    #     recv_msg.ParseFromString(bytesAddressPair[0])
    #     print recv_msg.command, recv_msg.node1_name, recv_msg.node2_name
    #
    #     if recv_msg.command == "deleteLink":
    #         net_node1 = net.getNodeByName(recv_msg.node1_name)
    #         net_node2 = net.getNodeByName(recv_msg.node2_name)
    #         if net.linksBetween(net_node1, net_node2):
    #             net.delLinkBetween(net_node1, net_node2)
    #
    #     if recv_msg.command == "addLink":
    #         net_node1 = net.getNodeByName(recv_msg.node1_name)
    #         net_node2 = net.getNodeByName(recv_msg.node2_name)
    #         net_node1.cmd("ifconfig")
    #         net_node2.cmd("ifconfig")
    #         net.addLink(net_node1, net_node2, cls=TCLink)

    net.stop()

setLogLevel('info')    # 'info' is normal; 'debug' is for when there are problems
main()
