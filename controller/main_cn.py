import argparse
import re
import time
import os
import numpy as np
import datetime

import threading
import Queue

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
import mc_msgs_pb2 as MCMsgs

import sys
sys.path.append("../")
from mobility.read_real_tles import *
from mobility.read_live_tles import *
from mobility.mobility_utils import *
from mobility.read_gs import *
from mininet_infra.create_mininet_topology import *
from routing.constellation_routing import *
from comm_protocol.controller_main import *

def get_all_mgnt_interfaces(filename):
    mIntf_File = open(filename, 'r')
    lines = mIntf_File.readlines()
    m_intf = []

    for i in range(len(lines)):
	lines[i].split("\t")[0]
        m_intf.append({"node": lines[i].split("\t")[0], "mgnt_ip": lines[i].split("\t")[1]})

    return m_intf

def get_management_ip(all_mgnt_ips, node):
    for interface in all_mgnt_ips:
	if interface["node"] == node:
		return interface["mgnt_ip"]

def get_time(filename):
    file = open(filename, 'r')
    lines = file.readlines()
    used_time = lines[0]

    year, month, day = used_time.split(" ")[0].split("-")
    hour, min, sec = used_time.split(" ")[1].split(":")
    min_num = 0
    min_num += float(min) + (float(sec)/float(60.0))
    ts = load.timescale()
    t2 = ts.utc(int(year), int(month), int(day), int(hour), min_num)

    return t2

def get_links(filename):
    linksFile = open(filename, 'r')
    lines = linksFile.readlines()
    links = []

    for i in range(len(lines)):
        links.append(lines[i].strip())

    return links

def get_intf(filename):
    Intf_file = open(filename, 'r')
    lines = Intf_file.readlines()
    list_of_Intf_IPs = []

    for i in range(len(lines)):
        intf, ip = lines[i].strip().split("\t")
        list_of_Intf_IPs.append({"Interface": intf, "IP": ip})

    return list_of_Intf_IPs

def main():

    number_of_orbits = 72
    ground_stations = read_gs("../mobility/ground_stations.txt")
    satellites = load.tle_file("https://celestrak.com/NORAD/elements/starlink.txt")
    satellites_by_name = {sat.name: sat for sat in satellites}
    satellites_by_index = {}


    orbital_data = get_orbital_planes("starlink.txt",1)

    t = get_time("time_log.txt")
    print t.utc_strftime()
    links = get_links("links_log.txt")
    list_of_Intf_IPs = get_intf("constellation_ip_assignment.txt")
    list_of_mgnt_IPs = get_all_mgnt_interfaces("m_intf_log.txt")

    print "num_links=", len(links), "num__mgn_interfaces=",len(list_of_Intf_IPs)

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

    print "num_satellites=", num_of_satellites, "num_gs="num_of_ground_stations

    conn_mat_size = num_of_satellites + num_of_ground_stations

    connectivity_matrix = [[0 for c in range(conn_mat_size)] for r in range(conn_mat_size)]
    connectivity_matrix = mininet_add_ISLs(connectivity_matrix, satellites_sorted_in_orbits, satellites_by_name, satellites_by_index, "SAME_ORBIT_AND_GRID_ACROSS_ORBITS", t)
    connectivity_matrix = mininet_add_GSLs(connectivity_matrix, satellites_by_name, satellites_by_index, ground_stations, 12, "BASED_ON_DISTANCE_ONLY_MININET", t)

    link_chara = calculate_link_charateristics_for_gsls_isls(connectivity_matrix, satellites_by_index, satellites_by_name, ground_stations, t)


    start = round(time.time()*1000)
    # sats = satellites_by_index[10]
    initial_routes = initial_routing(satellites_by_index, ground_stations, connectivity_matrix)

    end = round(time.time()*1000)
    print "Initial routing took ", end-start, "ms ", "for ", len(initial_routes), " routes"

    # initial_routes = []
    # static_routing_update_commands(initial_routes, links, list_of_Intf_IPs, satellites_by_index)
    # exit()
    for route in initial_routes:
        if len(route[0]) > 2:
            parameters = get_static_route_parameter(route, links, list_of_Intf_IPs, satellites_by_index)
        #

            msg                         = MCMsgs.mega_constellation_msg()
            msg.message_type            =  2
            msg.message_command         = "ip route"
            msg.message_receiver        = parameters[0]
            msg.route_update_type       = 0

            msg.route_destination       = parameters[1]
            msg.route_next_hop          = parameters[2]
            msg.route_out_interface     = parameters[3]

            msg.change_route_time       = t.utc_strftime()

            print msg
            sendto_ip = get_management_ip(list_of_mgnt_IPs, parameters[0])
            serverAddressPort=(str(sendto_ip.strip()), 20001)
            UDPClientSocket = socket(family=AF_INET, type=SOCK_DGRAM)
            UDPClientSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
            UDPClientSocket.sendto(msg.SerializeToString(), serverAddressPort)
            UDPClientSocket.close()

            time.sleep(0.002)
            msg                         = MCMsgs.mega_constellation_msg()
            msg.message_type            =  2
            msg.message_command         = "ip route"
            msg.message_receiver        = parameters[4]
            msg.route_update_type       = 0

            msg.route_destination       = parameters[5]
            msg.route_next_hop          = parameters[6]
            msg.route_out_interface     = parameters[7]

            msg.change_route_time       = t.utc_strftime()

            print msg
            sendto_ip = get_management_ip(list_of_mgnt_IPs, parameters[4])
            serverAddressPort=(str(sendto_ip.strip()), 20001)
            UDPClientSocket = socket(family=AF_INET, type=SOCK_DGRAM)
            UDPClientSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
            UDPClientSocket.sendto(msg.SerializeToString(), serverAddressPort)
            UDPClientSocket.close()
            time.sleep(0.002)
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

main()
