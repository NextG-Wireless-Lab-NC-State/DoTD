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
import wget

import sys
sys.path.append("../")
from mobility.read_real_tles import *
from mobility.read_live_tles import *
from mobility.mobility_utils import *
from mobility.read_gs import *
from mininet_infra.create_mininet_topology import *
from routing.routing_utils import *
from routing.constellation_routing import *
from comm_protocol.controller_main import *

def log_info_for_controller(current_time, links, m_intfs, satellites, routes):
    time_log = open("time_log.txt", "w")
    time_log.write(current_time + "\n")

    links_log = open("links_log.txt", "w")
    for link in links:
        links_log.write(link + "\n")
    links_log.close()

    m_intf_log = open("m_intf_log.txt", "w")
    for intf in m_intfs:
        m_intf_log.write(intf["node"] + "\t" + intf["mgnt_ip"] + "\n")
    m_intf_log.close()

    satellites_log = open("satellites_by_index_log.txt", "w")
    for sat in satellites:
        satellites_log.write(str(sat) + "\n")
    satellites_log.close()

    for route in routes:
        if len(route[0]) > 2:
            current_route = route[0]
            src_node, next_hop_node, dest_node, last_hop_node = current_route[0], current_route[1], current_route[len(current_route)-1], current_route[len(current_route)-2]
            src_node = "sat"+str(src_node) if src_node < len(satellites) else "gs"+str(src_node%len(satellites))
            routes_log = open("routes/"+str(src_node)+"_routes.txt", "a")
            routes_log.write(str(current_route)[1:-1] + "\n")
            routes_log.close()

    print("..... Logged!\n")

def main():
    N = 3


    for f in os.listdir('routes/'):
        os.remove(os.path.join('routes/', f))

    print "All old routes have been removed ... "

    number_of_orbits = 72
    ground_stations = read_gs("../mobility/ground_stations.txt")
    satellites = load.tle_file("https://celestrak.com/NORAD/elements/starlink.txt")
    satellites_by_name = {sat.name: sat for sat in satellites}
    satellites_by_index = {}

    if os.path.isfile("./starlink.txt"):
        os.remove("./starlink.txt")

    tle_url = "https://celestrak.com/NORAD/elements/supplemental/starlink.txt"
    tle_file = wget.download(tle_url)

    orbital_data = get_orbital_planes("starlink.txt",1)
    # print orbital_data
    ts = load.timescale()
    t = ts.now()
    print "\n"
    print t.tt
    print t.utc_strftime()
    dt, leap_second = t.utc_datetime_and_leap_second()
    print dt
    newscs = ((str(dt).split(" ")[1]).split(":")[2]).split("+")[0]
    date, timeN, zone = t.utc_strftime().split(" ")
    year, month, day = date.split("-")
    hour, minute, second = timeN.split(":")
    loggedTime = str(year)+","+str(month)+","+str(day)+","+str(hour)+","+str(minute)+","+str(newscs)
    t2 = ts.utc(int(year), int(month), int(day), int(hour), int(minute), float(newscs))
    print t2.tt

    satellites_sorted_in_orbits = []        #carry satellites names according to STARLINK naming conversion
    for i in range(number_of_orbits):
        satellites_in_orbit = []
        for data in orbital_data:
            if i == int(orbital_data[str(data)][2]):
                satellites_in_orbit.append(satellites_by_name[str(data)])

        satellites_sorted_in_orbits.append(sort_satellites_in_orbit(satellites_in_orbit, t))

    sat_index = -1
    for orbit in satellites_sorted_in_orbits:
        for i in range(len(orbit)):
            sat_index += 1
            satellites_by_index[sat_index] = orbit[i].name

    num_of_satellites = len(orbital_data)
    num_of_ground_stations = len(ground_stations)

    print num_of_satellites, num_of_ground_stations

    conn_mat_size = num_of_satellites + num_of_ground_stations

    connectivity_matrix = [[0 for c in range(conn_mat_size)] for r in range(conn_mat_size)]
    connectivity_matrix = mininet_add_ISLs(connectivity_matrix, satellites_sorted_in_orbits, satellites_by_name, satellites_by_index, "SAME_ORBIT_AND_GRID_ACROSS_ORBITS", t)
    connectivity_matrix = mininet_add_GSLs(connectivity_matrix, satellites_by_name, satellites_by_index, ground_stations, 12, "BASED_ON_DISTANCE_ONLY_MININET", t)

    link_chara = calculate_link_charateristics_for_gsls_isls(connectivity_matrix, satellites_by_index, satellites_by_name, ground_stations, t)

    # for i in range(len(link_chara["latency_matrix"])):
    #     for j in range(len(link_chara["latency_matrix"][i])):
    #         if link_chara["latency_matrix"][i][j] != 0:
    #             print link_chara["latency_matrix"][i][j], i, j
    #
    #
    # for i in range(len(link_chara["throughput_matrix"])):
    #     for j in range(len(link_chara["throughput_matrix"][i])):
    #         if link_chara["throughput_matrix"][i][j] != 0:
    #             print link_chara["throughput_matrix"][i][j], i, j


    available_ips = generate_ips_for_constellation()

    start = round(time.time()*1000)
    initial_routes = initial_routing(satellites_by_index, ground_stations, connectivity_matrix)
    end = round(time.time()*1000)
    print "Initial routing took ", end-start, "ms ", "for ", len(initial_routes), " routes"

    # start = round(time.time()*1000)
    # initial_routes = initial_routing(satellites_by_index, ground_stations, connectivity_matrix)
    #
    # end = round(time.time()*1000)
    # print "Initial routing took ", end-start, "ms"

    topology = sat_network(N=N)
    topg = topology.create_sat_network(satellites=satellites_by_index, ground_stations=ground_stations, connectivity_matrix=connectivity_matrix, link_throughput=link_chara["throughput_matrix"], link_latency=link_chara["latency_matrix"])
    log_info_for_controller(loggedTime, topg["isl_gls_links"], topg["management_interface"], satellites_by_index, initial_routes);
    net = Mininet(topo = topology, link=TCLink, autoSetMacs = True)
    net.start()
    list_of_Intf_IPs = topology.initial_ipv4_assignment_for_interfaces(net, available_ips)
    # cmds_list = []
    # routesfile = open("routes_file.txt", "w")
    # start = round(time.time()*1000)
    # for route in initial_routes:
    #     routesfile.write(str(route) + "\n")
    #     topology.configure_initial_static_route(net, route[0], num_of_satellites, num_of_ground_stations, cmds_list)
    #
    # routesfile.close()
    # end = round(time.time()*1000)
    # print "Configure inital routes took ", end-start, "ms"
    # print len(connectivity_matrix)

    # for route in initial_routes:
    #     print route
    # topology.startListener(net, available_satellites_by_name, ground_stations, topg["management_interface"])
    # topology.startworker(net, satellites_by_index, ground_stations, topg["management_interface"])
    topology.startRoutingConfig(net, satellites_by_index, ground_stations, topg["management_interface"])
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
