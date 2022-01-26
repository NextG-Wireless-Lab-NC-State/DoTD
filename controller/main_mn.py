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
import shutil

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

def find_route_between_src_dest(src_sat, dest_sat, constellation_routes):
    if src_sat < dest_sat:
        for route in constellation_routes[src_sat]:
            # print route
            current_route = route[0][:]
            if "sat"+str(src_sat) == "sat"+str(current_route[0]) and "sat"+str(dest_sat) == "sat"+str(current_route[len(current_route)-1]):
                return current_route

    # This is added because in constellation_routes and in initial_routes, we only store the route from x to y but not the route for y to x.
    # We do that to minimize the calcuations. Therefore, sometimes if src_sat > dest_sat, we need to search in the opposite direction
    if src_sat > dest_sat:
        for route in constellation_routes[dest_sat]:
            current_route = route[0][:]
            if "sat"+str(src_sat) == "sat"+str(current_route[len(current_route)-1]) and "sat"+str(dest_sat) == "sat"+str(current_route[0]):
                retr_route = route[0][:]
                retr_route.reverse()
                return retr_route

    return -1

def get_gs_ip(list_of_Intf_IPs, gs):
    for pair in list_of_Intf_IPs:
        if gs in pair["Interface"]:
            return pair["IP"]

def get_sats_by_index(filename):
    satsFile = open(filename, 'r')
    lines = satsFile.readlines()
    satellites = []

    for i in range(len(lines)):
        satellites.append(lines[i].strip())

    return satellites

def get_sats_by_name(filename):
    satsFile = open(filename, 'r')
    lines = satsFile.readlines()
    satellites = []

    for i in range(len(lines)):
        satellites.append(lines[i].strip())

    return satellites

def log_info_for_controller(current_time, links, m_intfs, satellites_by_index, satellites_by_name, routes, GS_SAT_Table):
    time_log = open("./data_gen/current_tle_data/time_log.txt", "w")
    time_log.write(current_time + "\n")

    links_log = open("./data_gen/current_tle_data/links_log.txt", "w")
    for link in links:
        links_log.write(link + "\n")
    links_log.close()

    m_intf_log = open("./data_gen/current_tle_data/m_intf_log.txt", "w")
    for intf in m_intfs:
        m_intf_log.write(intf["node"] + "\t" + intf["mgnt_ip"] + "\n")
    m_intf_log.close()

    satellitesInd_log = open("./data_gen/current_tle_data/satellites_by_index_log.txt", "w")
    for sat in satellites_by_index:
        satellitesInd_log.write(str(sat) + "\n")
    satellitesInd_log.close()

    satellitesName_log = open("./data_gen/current_tle_data/satellites_by_name_log.txt", "w")
    for sat in satellites_by_name:
        satellitesName_log.write(str(sat) + "\n")
    satellitesName_log.close()

    for route in routes:
        if len(route[0]) > 2:
            current_route = route[0][:]
            src_node, next_hop_node, dest_node, last_hop_node = current_route[0], current_route[1], current_route[len(current_route)-1], current_route[len(current_route)-2]
            src_node = "sat"+str(src_node) if src_node < len(satellites_by_index) else "gs"+str(src_node%len(satellites_by_index))
            dest_node = "sat"+str(dest_node) if dest_node < len(satellites_by_index) else "gs"+str(dest_node%len(satellites_by_index))
            routes_log = open("./data_gen/current_tle_data/routes/"+str(src_node)+"_routes.txt", "a")
            routes_log.write(str(current_route)[1:-1] + "\n")
            routes_log.close()

            routes_log = open("./data_gen/current_tle_data/routes/"+str(dest_node)+"_routes.txt", "a")
            current_route.reverse()
            routes_log.write(str(current_route)[1:-1] + "\n")
            routes_log.close()

    for index, gs_sat in enumerate(GS_SAT_Table):
        gs_sat_log = open("./data_gen/current_tle_data/GS_SAT_Table.txt", "a")
        if len(gs_sat) > 0:
            gs_sat_log.write(str(index)+"\t"+str(gs_sat)[1:-1] + "\n")

        gs_sat_log.close()

    print("..... Logged!\n")

def main():
    USE_OLD_ROUTE_FILES = False
    simulation_time_in_seconds = 60
    step_in_seconds = 1

    N = 3
    number_of_orbits = 72

    if USE_OLD_ROUTE_FILES == False:
        file_source = 'data_gen/current_tle_data'
        file_destination = 'data_gen/old_tle_data/'

        if os.path.isfile(file_source+"/time_log.txt"):
            file = open(file_source+"/time_log.txt", 'r')
            lines = file.readlines()
            used_time = lines[0].strip().split(",")
            file_postfix = ""
            for tm in used_time:
                file_postfix += "_"+tm

            old_directory_name = "data"+file_postfix
            path = os.path.join(file_destination, old_directory_name)

            if os.path.exists(path):
                shutil.rmtree(path)

            dest = shutil.copytree(file_source, path)

        else:
            print "No current files ... "

        for f in os.listdir('data_gen/current_tle_data/routes/'):
            os.remove(os.path.join('data_gen/current_tle_data/routes/', f))

        print "All old routes have been removed ... "

        ground_stations = read_gs("../mobility/ground_stations.txt")
        satellites = load.tle_file("https://celestrak.com/NORAD/elements/starlink.txt")
        satellites_by_name = {sat.name: sat for sat in satellites}
        satellites_by_index = {}

        if os.path.isfile("./data_gen/current_tle_data/starlink.txt"):
            os.remove("./data_gen/current_tle_data/starlink.txt")

        tle_url = "https://celestrak.com/NORAD/elements/supplemental/starlink.txt"
        tle_file = wget.download(tle_url, out = "./data_gen/current_tle_data/")

        # orbital_data = get_orbital_planes("./data_gen/starlink.txt",1)
        # orbital_data = get_orbital_planes_ML("./data_gen/current_tle_data/starlink.txt",1)

        orbital_data = get_orbital_planes_classifications("./data_gen/current_tle_data/starlink.txt",1)

        ts = load.timescale()
        t = ts.now()
        print t.utc_strftime()

        dt, leap_second = t.utc_datetime_and_leap_second()
        newscs = ((str(dt).split(" ")[1]).split(":")[2]).split("+")[0]
        date, timeN, zone = t.utc_strftime().split(" ")
        year, month, day = date.split("-")
        hour, minute, second = timeN.split(":")
        loggedTime = str(year)+","+str(month)+","+str(day)+","+str(hour)+","+str(minute)+","+str(newscs)
        t2 = ts.utc(int(year), int(month), int(day), int(hour), int(minute), float(newscs))
        print t2.tt
    ######
    elif USE_OLD_ROUTE_FILES == True:
        ground_stations = read_gs("../mobility/ground_stations.txt")
        satellites = load.tle_file("https://celestrak.com/NORAD/elements/starlink.txt")
        satellites_by_name_from_file = get_sats_by_name("./data_gen/current_tle_data/satellites_by_name_log.txt")

        satellites_by_name = {sat.name: sat for sat in satellites if sat.name in satellites_by_name_from_file}
        satellites_by_index = get_sats_by_index("./data_gen/current_tle_data/satellites_by_index_log.txt")

        orbital_data = get_orbital_planes_ML("./data_gen/current_tle_data/starlink.txt",1)

        file = open("./data_gen/current_tle_data/time_log.txt", 'r')
        lines = file.readlines()
        used_time = lines[0]

        year, month, day, hour, minute, newscs = used_time.split(",")
        ts = load.timescale()
        t = ts.utc(int(year), int(month), int(day), int(hour), int(minute), float(newscs))
        print t.tt

    satellites_sorted_in_orbits = []        #carry satellites names according to STARLINK naming conversion
    for i in range(number_of_orbits):
        satellites_in_orbit = []
        cn = 0
        for data in orbital_data:
            if i == int(orbital_data[str(data)][2]):
                satellites_in_orbit.append(satellites_by_name[str(data)])
                print i, data, orbital_data[str(data)]
                cn +=1
        print i, cn

        satellites_sorted_in_orbits.append(sort_satellites_in_orbit(satellites_in_orbit, t))

    sat_index = -1
    for orbit in satellites_sorted_in_orbits:
        for i in range(len(orbit)):
            sat_index += 1
            satellites_by_index[sat_index] = orbit[i].name
            # print sat_index, satellites_by_index[sat_index]

    num_of_satellites = len(orbital_data)
    num_of_ground_stations = len(ground_stations)
    GS_SAT_Table = [[] for i in range(num_of_satellites)]

    print num_of_satellites, num_of_ground_stations

    conn_mat_size = num_of_satellites + num_of_ground_stations
    connectivity_matrix = [[0 for c in range(conn_mat_size)] for r in range(conn_mat_size)]
    connectivity_matrix = mininet_add_ISLs(connectivity_matrix, satellites_sorted_in_orbits, satellites_by_name, satellites_by_index, "SAME_ORBIT_AND_GRID_ACROSS_ORBITS", t)
    connectivity_matrix = mininet_add_GSLs(connectivity_matrix, satellites_by_name, satellites_by_index, ground_stations, 12, "BASED_ON_DISTANCE_ONLY_MININET", t, 1, GS_SAT_Table)

    link_chara = calculate_link_charateristics_for_gsls_isls(connectivity_matrix, satellites_by_index, satellites_by_name, ground_stations, t)

    available_ips = generate_ips_for_constellation()

    last_CMatrix = connectivity_matrix[:]
    last_GS_SAT_Table = GS_SAT_Table[:]

    if USE_OLD_ROUTE_FILES == False:
        start = round(time.time()*1000)
        initial_routes = initial_routing_v2(satellites_by_index, ground_stations, connectivity_matrix, link_chara["latency_matrix"])
        end = round(time.time()*1000)
        print "Initial routing took ", end-start, "ms ", "for ", len(initial_routes), " routes"

    # for route in initial_routes:
    #     print route
    start = round(time.time()*1000)

    copy_initial_routes = initial_routes[:]
    constellation_routes = {k: [] for k in range(num_of_satellites)}
    for route in copy_initial_routes:
        current_route = route[0]
        i = current_route[0]
        constellation_routes[i].append(route)

    # for i in range(num_of_satellites):
    #     for route in copy_initial_routes:
    #         current_route = route[0]
    #         if "sat"+str(i) == "sat"+str():
    #             if route not in constellation_routes[i]:
    #                 constellation_routes[i].append(route)

    end = round(time.time()*1000)
    print "------ constellation_routes ", end-start, "ms "

    # route_to_sat_GW = find_route_between_src_dest(51, 50, constellation_routes)
    # print route_to_sat_GW
    #
    # for key, values in itertools.izip(constellation_routes.keys(), constellation_routes.values()):
    #     for value in values:
    #         print key, value
    # for i in range(num_of_satellites):
    #     route_to_sat_GW = find_route_between_src_dest(0, i, constellation_routes)
    #     print route_to_sat_GW
    #
    # exit()
    # start = round(time.time()*1000)
    # initial_routes = initial_routing(satellites_by_index, ground_stations, connectivity_matrix)
    #
    # end = round(time.time()*1000)
    # print "Initial routing took ", end-start, "ms"


    topology = sat_network(N=N)
    topg = topology.create_sat_network(satellites=satellites_by_index, ground_stations=ground_stations, connectivity_matrix=connectivity_matrix, link_throughput=link_chara["throughput_matrix"], link_latency=link_chara["latency_matrix"])
    if USE_OLD_ROUTE_FILES == False:
        log_info_for_controller(loggedTime, topg["isl_gls_links"], topg["management_interface"], satellites_by_index, satellites_by_name, initial_routes, GS_SAT_Table);

    net = Mininet(topo = topology, link=TCLink, autoSetMacs = True)
    net.start()
    list_of_Intf_IPs = topology.initial_ipv4_assignment_for_interfaces(net, available_ips)

    old_secs = newscs
    ts = load.timescale()
    addthis = 0;
    #
    # start = round(time.time()*1000)
    # constellation_routes = {k: [] for k in range(num_of_satellites)}
    # for i in range(num_of_satellites):
    #     for route in initial_routes:
    #         current_route = route[0]
    #         if "sat"+str(i) == "sat"+str(current_route[0]):
    #             if route not in constellation_routes[i]:
    #                 constellation_routes[i].append(route)
    #
    # for key, values in itertools.izip(constellation_routes.keys(), constellation_routes.values()):
    #     for value in values:
    #         print key, value
    #
    # end = round(time.time()*1000)
    # print "------ constellation_routes ", end-start, "ms "

    links_updated = topg["isl_gls_links"][:]

    while simulation_time_in_seconds > 0:
        simulation_time_in_seconds -= step_in_seconds
        addthis += step_in_seconds
        t2 = ts.utc(int(year), int(month), int(day), int(hour), int(minute), float(newscs)+addthis)
        print t2.utc_strftime()


        new_GS_SAT_Table = [[] for i in range(num_of_satellites)]
        new_CMatrix = [[0 for c in range(conn_mat_size)] for r in range(conn_mat_size)]

        new_CMatrix = mininet_add_ISLs(new_CMatrix, satellites_sorted_in_orbits, satellites_by_name, satellites_by_index, "SAME_ORBIT_AND_GRID_ACROSS_ORBITS", t2)
        new_CMatrix = mininet_add_GSLs(new_CMatrix, satellites_by_name, satellites_by_index, ground_stations, 12, "BASED_ON_DISTANCE_ONLY_MININET", t2, 1, new_GS_SAT_Table)

        # for index, vals in enumerate(new_GS_SAT_Table):
        #     if len(vals) > 0:
        #         print index, vals

        route_changes = check_changes_in_routes(last_CMatrix, new_CMatrix)

        print len(route_changes)

        gsl_ch = 0
        isl_ch = 0
        update_gsl_routing_cmd = []
        if len(route_changes) < 1000:
            for change in route_changes:
                start = round(time.time()*1000)
                print change
                if change[0] < num_of_satellites and change[1] >= num_of_satellites:
                    gs_number = int(change[1])%num_of_satellites
                    gs_ip = get_gs_ip(list_of_Intf_IPs, "gs"+str(gs_number)+"-eth1").split("/")[0]
                    gs_network_address = get_network_address(gs_ip)

                    for i in range(num_of_satellites):
                        route_to_sat_GW = find_route_between_src_dest(i, change[0], constellation_routes)
                        if route_to_sat_GW != -1:
                            parameters = get_static_route_parameter([route_to_sat_GW], links_updated, list_of_Intf_IPs, satellites_by_index);
                            if len(parameters) > 0:
                                if change[2] == 0 and change[3] == 1:
                                    update_gsl_routing_cmd.append("ip route add "+str(gs_network_address)+" via "+str(parameters[2])+" dev "+str(parameters[3]))
                                elif change[2] == 1 and change[3] == 0:
                                    update_gsl_routing_cmd.append("ip route del "+str(gs_network_address)+" via "+str(parameters[2])+" dev "+str(parameters[3]))
                        else:
                            print "Error: cannot find the route between sat", i, " and sat", change[0]
                            # exit()
                    gsl_ch += 1

            # changes in the ISL links
                elif change[0] < num_of_satellites and change[1] < num_of_satellites:
                    isl_ch += 1

                end = round(time.time()*1000)
                print "one iteration of change --- ", end-start, "ms "
                
            if len(update_gsl_routing_cmd) > 0:
                start = round(time.time()*1000)
                updates_log = open("./data_gen/current_tle_data/routing_updates_"+str(t2.utc_strftime())+"_.txt", "w")
                for update in update_gsl_routing_cmd:
                    updates_log.write(str(update) + "\n")

                end = round(time.time()*1000)
                print "writing to file ", end-start, "ms "

                updates_log.close()

            print gsl_ch, isl_ch

        last_CMatrix = new_CMatrix[:]

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
    # I will need to add a function here to read these "updates_log = open("./data_gen/current_tle_data/routing_updates_"+str(t2.utc_strftime())+"_.txt", "w")" files and update the routing info.
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
