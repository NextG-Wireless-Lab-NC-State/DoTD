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
        print "Assign IP message is sent to "+str(sat)+" with IP address "+intf_ips["IP"]+" on interface = "+intf_ips["Interface"]
        time.sleep(0.02)

def available_interface(node, links):
    # print node
    maximum_interface_number = 0
    for link in links:
        if node+"-" in link:
            sublink1, sublink2 = link.split(":")
            if node in sublink1:
                if int(sublink1.split("-")[1][3:]) > maximum_interface_number:
                    maximum_interface_number = int(sublink1.split("-")[1][3:])
            if node in sublink2:
                if int(sublink2.split("-")[1][3:]) > maximum_interface_number:
                    maximum_interface_number = int(sublink2.split("-")[1][3:])
    return maximum_interface_number

def update_links(links, node1, node2, action):
    found = 0
    if action == "delete":
        found = -1
        for link in links:
            if node1 in link and node2 in link:
                links.remove(link)
                found = 0
                print "[Update links] The following link "+link+" is removed from the links list"
    elif action == "add":
        node1_ava_interface = available_interface(node1, links)+1
        node2_ava_interface = available_interface(node2, links)+1
        new_link = node1+"-eth"+str(node1_ava_interface)+":"+node2+"-eth"+str(node2_ava_interface)
        links.append(new_link)
        print "[Update links] The following link "+new_link+" is added to the links list"

    if found == -1:
        print "Error -- "+node1+" and "+node2+" link is not found. check the links list between mininet and controller"
        exit()

    return links

def crtl_mininet_update_topology(gsl_changes, links, list_of_Intf_IPs, nodes_mgnt_intf):
    for i in range(len(gsl_changes)):
        link_intfs_ips = get_link_intfs_ips("sat"+str(gsl_changes[i][1]), "gs"+str(gsl_changes[i][0]), links, list_of_Intf_IPs)

        command_message = create_message_to_mininet("deleteLink", "sat"+str(gsl_changes[i][1]), "gs"+str(gsl_changes[i][0]))
        serverAddressPort=("131.227.207.216", 20001)
        send_command(command_message, serverAddressPort)
        links = update_links(links, "sat"+str(gsl_changes[i][1]), "gs"+str(gsl_changes[i][0]), "delete")

        command_message = create_message_to_mininet("addLink", "sat"+str(gsl_changes[i][2]), "gs"+str(gsl_changes[i][0]))
        serverAddressPort=("131.227.207.216", 20001)
        send_command(command_message, serverAddressPort)
        links = update_links(links, "sat"+str(gsl_changes[i][2]), "gs"+str(gsl_changes[i][0]), "add")
        time.sleep(0.01)
        # for link in links:
        #     if "sat"+str(gsl_changes[i][1]) in link and "gs"+str(gsl_changes[i][0]) in link:


        # update the ip address for the satellite node
        new_intf_name = "sat"+str(gsl_changes[i][2])+"-eth"+str(available_interface("sat"+str(gsl_changes[i][2]), links))
        command_message = create_message_to_nodes("Assign IP", "sat"+str(gsl_changes[i][2]), "ifconfig", [new_intf_name, link_intfs_ips[0]["IP"]])
        ip_addr = get_management_ip(nodes_mgnt_intf, "sat"+str(gsl_changes[i][2]))
        serverAddressPort=(str(ip_addr.strip()), 20001)
        send_command(command_message, serverAddressPort)
        time.sleep(0.01)
        # update the ip address for the ground_station node
        new_intf_name = "gs"+str(gsl_changes[i][0])+"-eth"+str(available_interface("gs"+str(gsl_changes[i][0]), links))
        command_message = create_message_to_nodes("Assign IP", "gs"+str(gsl_changes[i][0]), "ifconfig", [new_intf_name, link_intfs_ips[1]["IP"]])
        ip_addr = get_management_ip(nodes_mgnt_intf, "gs"+str(gsl_changes[i][0]))
        serverAddressPort=(str(ip_addr.strip()), 20001)
        send_command(command_message, serverAddressPort)
        time.sleep(0.01)

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

    for link in mininetExtract["links"]:
        print link

    for lm in G["GSL_Connectivity"]:
        print lm
    available_ips = generate_ips_for_constellation()
    list_of_Intf_IPs = assign_ips_for_constellation(mininetExtract["links"], available_ips)
    crtl_mininet_ip_assignment(list_of_Intf_IPs, mininetExtract2)

    while(True):
        ts = load.timescale()
        t = ts.now()
        print('UTC date and time:', t.utc_strftime())
        old_gsls = G["GSL_Connectivity"][:]
        G = graph_add_GSLs(G["Graph"], available_satellites_by_name, actual_sat_number_to_counter, ground_stations, t, 12, "BASED_ON_DISTANCE_ONLY_GRAPH")
        gsls_differences = get_differences_in_GSLs_between_iterations(old_gsls, G["GSL_Connectivity"])
        print gsls_differences
        crtl_mininet_update_topology(gsls_differences, mininetExtract["links"], list_of_Intf_IPs, mininetExtract2)
main()
