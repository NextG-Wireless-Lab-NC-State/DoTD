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
from routing.routing_utils import *
from comm_protocol.controller_main import *

def extract_links(filename):
    linksFile = open(filename, 'r')
    lines = linksFile.readlines()
    links = []
    used_time = lines[0]

    for i in range(1, len(lines)):
        links.append(lines[i].strip())

    year, month, day = used_time.split(" ")[0].split("-")
    hour, min, sec = used_time.split(" ")[1].split(":")
    min_num = 0
    min_num += float(min) + (float(sec)/float(60.0))
    ts = load.timescale()
    t2 = ts.utc(int(year), int(month), int(day), int(hour), min_num)

    return {"used_time" : t2,
	    "links" : links
	   }

def extract_management_interfaces(filename):
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

def crtl_mininet_ip_assignment(list_of_Intf_IPs, nodes_mgnt_intf):
    for intf_ips in list_of_Intf_IPs:
        sat, interface = intf_ips["Interface"].split("-")
        ip_addr = get_management_ip(nodes_mgnt_intf, sat)
        command_message = create_message_to_nodes("Assign IP", sat, "ifconfig", [intf_ips["Interface"], intf_ips["IP"]])
        serverAddressPort=(str(ip_addr.strip()), 20001)
        send_command(command_message, serverAddressPort)
        time.sleep(0.02)

def crtl_mininet_update_topology(gsl_changes):
    for i in range(len(gsl_changes)):
        command_message = create_message_to_mininet("deleteLink", "sat"+str(gsl_changes[i][1]), "gs"+str(gsl_changes[i][0]))
        serverAddressPort=("172.16.0.3", 20001)
        send_command(command_message, serverAddressPort)

    for i in range(len(gsl_changes)):
        command_message = create_message_to_mininet("addLink", "sat"+str(gsl_changes[i][2]), "gs"+str(gsl_changes[i][0]))
        serverAddressPort=("172.16.0.3", 20001)
        send_command(command_message, serverAddressPort)

def main():
    N = 3

    satellites = load.tle_file("https://celestrak.com/NORAD/elements/starlink.txt")
    satellites_by_name = {sat.name: sat for sat in satellites}
    planes = extract_planes("../mobility/starlink_tles.txt")

    cur_planes = planes["Planes"]
    print len(planes["Unassigned"])

    mininetExtract = extract_links("links_log.txt")
    mininetExtract2 = extract_management_interfaces("m_intf_log.txt")

    sorted_planes = sort_satellites_within_plane(cur_planes, satellites_by_name, mininetExtract["used_time"])

    # Get the satellites in planes only, igonore the Unassigned satellites
    available_satellites = []
    for key in sorted_planes.keys():
        sats = ""
        for satellite in sorted_planes[key]:
            sats += str(satellites_by_name[str(satellite)].name).split("-")[1]+","
            available_satellites.append(satellites_by_name[str(satellite)])

    available_satellites_by_name = {sat.name: sat for sat in available_satellites}
    actual_sat_number_to_counter = label_satellites_properly(sorted_planes, len(available_satellites_by_name))

    ground_stations = read_gs("../mobility/ground_stations.txt")

    num_of_satellites = len(available_satellites_by_name)
    num_of_ground_stations = len(ground_stations)

    print num_of_satellites, num_of_ground_stations
    conn_mat_size = num_of_satellites + num_of_ground_stations

    G = nx.Graph()
    G = graph_add_ISLs(G, available_satellites_by_name, actual_sat_number_to_counter, sorted_planes, 0, 0, "SAME_ORBIT_AND_BASED_ON_DISTANCE_FOR_INTER_ORBIT", mininetExtract["used_time"])
    G = graph_add_GSLs(G, available_satellites_by_name, actual_sat_number_to_counter, ground_stations, mininetExtract["used_time"], 12, "BASED_ON_DISTANCE_ONLY_GRAPH")

    # available_ips = generate_ips_for_constellation()
    # list_of_Intf_IPs = assign_ips_for_constellation(mininetExtract["links"], available_ips)
    # crtl_mininet_ip_assignment(list_of_Intf_IPs, mininetExtract2)

    while 1:
        ts = load.timescale()
        t = ts.now()
        print('UTC date and time:', t.utc_strftime())
        old_gsls = G["GSL_Connectivity"][:]
        G = graph_add_GSLs(G["Graph"], available_satellites_by_name, actual_sat_number_to_counter, ground_stations, t, 12, "BASED_ON_DISTANCE_ONLY_GRAPH")
        gsls_differences = get_differences_in_GSLs_between_iterations(old_gsls, G["GSL_Connectivity"])
        print gsls_differences
        crtl_mininet_update_topology(gsls_differences)
main()
