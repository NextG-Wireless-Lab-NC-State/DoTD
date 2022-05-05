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
import enum

import sys
sys.path.append("../")
from mobility.read_live_tles import *
from mobility.mobility_utils import *
from mobility.read_gs import *
from mininet_infra.create_mininet_topology import *
from routing.routing_utils import *
from routing.constellation_routing import *
from comm_protocol.controller_main import *

DEBUG = 1

class TestbedMode(enum.Enum):
   SWOnly = 1
   SWPLUSHW = 2

def ping_thread(net):
    test_node = net.getNodeByName("gs13")
    test_node.cmd("date >> dump_99100.txt")
    test_node.cmd("ping 10.1.55.66 >> dump_99100.txt")

def get_gs_sat_pairs(connectivity_matrix, num_of_satellites):
    pairs = []
    for i in range(len(connectivity_matrix)):
        for j in range(len(connectivity_matrix[i])):
            if connectivity_matrix[i][j] == 1 and i < num_of_satellites and j > num_of_satellites:
                pairs.append((i, j))

    return pairs

def update_loop(data_path, net, updates_files_name, num_of_satellites):
    filename = data_path+"/allchanges_log_"+str(updates_files_name)+"_.txt"
    updatefile = open(filename, 'r')
    updates = updatefile.readlines()

    if len(updates) < 1:
        time.sleep(1)
        return net

    for update in updates:
        update_links = update.split(",")       #330,1575,0,1
        node1 = "sat"+str(update_links[0]) if int(update_links[0]) < num_of_satellites else "gs"+str(int(update_links[0])%num_of_satellites)
        node2 = "sat"+str(update_links[1]) if int(update_links[1]) < num_of_satellites else "gs"+str(int(update_links[1])%num_of_satellites)
        if node1 == "gs13" or node1 == "gs14" or node2 == "gs13" or node2 == "gs14":
            print update_links
        # print node1, node2
        net_node1 = net.getNodeByName(node1)
        net_node2 = net.getNodeByName(node2)

        if update_links[2] == 1 and update_links[3].strip() == 0:
            if net.linksBetween(net_node1, net_node2):
                net.delLinkBetween(net_node1, net_node2)

    for update in updates:
        update_links = update.split(",")       #330,1575,0,1
        node1 = "sat"+str(update_links[0]) if int(update_links[0]) < num_of_satellites else "gs"+str(int(update_links[0])%num_of_satellites)
        node2 = "sat"+str(update_links[1]) if int(update_links[1]) < num_of_satellites else "gs"+str(int(update_links[1])%num_of_satellites)
        if node1 == "gs13" or node1 == "gs14" or node2 == "gs13" or node2 == "gs14":
            print update_links
        # print node1, node2
        net_node1 = net.getNodeByName(node1)
        net_node2 = net.getNodeByName(node2)
        if update_links[2] == 0 and update_links[3].strip() == 1:
            net.addLink(net_node1, net_node2, cls=TCLink)

            # gs_node_IP = get_node_intf_ip(str(node2)+"-eth1", list_of_Intf_IPs)
            # oct1, oct2, oct3, oct4 = gs_node_IP.split(".")
            # new_sat_IP = str(oct1)+str(oct2)+str(oct3)+str(oct4-1)
            # net.addLink(net_node1, net_node2, cls=TCLink, params1 = {'ip' : new_sat_IP+"/28"}, params2 = {'ip' : gs_node_IP+"/28"})

    for i in range(0, num_of_satellites):
        sat_node = net.getNodeByName("sat"+str(i))
        sat_node.cmd("./"+data_path+"/routes_updates_"+str(updates_files_name)+"/sat"+str(i)+"_routes.sh &")

    return net

def read_staticParameters(routes, links, list_of_Intf_IPs, satellite_by_index, AllRoutesParameters):
    for route in routes:
        parameters = get_static_route_parameter(route, links, list_of_Intf_IPs, satellite_by_index)
        if len(parameters) > 0:
            AllRoutesParameters[(parameters[0], parameters[4])] = (parameters[0], parameters[1], parameters[2], parameters[3], parameters[4], parameters[5], parameters[6], parameters[7])

def read_IProute_files_thread(routes, initial_routes):
    for route in routes:
        route_new = []
        route_list = re.split(", | |\n", route)
        route = [int(r) for r in route_list if r.strip()]
        route_new.append(route)
        initial_routes.append(route_new)

def get_topology_routes(FreshRun, data_path, num_of_satellites, satellites_by_index, ground_stations, connectivity_matrix, links_charateristics):
    if FreshRun == True:
        start = round(time.time()*1000)
        initial_routes = initial_routing_v2(satellites_by_index, ground_stations, connectivity_matrix, links_charateristics["latency_matrix"])
        end = round(time.time()*1000)
        if DEBUG == 1:
            print "Initial routing calculations took ", end-start, "ms ", "for ", len(initial_routes), " routes"

        copy_initial_routes = initial_routes[:]
        constellation_routes = {k: [] for k in range(num_of_satellites)}
        for route in copy_initial_routes:
            current_route = route[0]
            i = current_route[0]
            constellation_routes[i].append(route)

    if FreshRun == False:
        start = round(time.time()*1000)
        constellation_routes = {m: [] for m in range(num_of_satellites)}
        initial_routes = []
        thread_list = []

        Rfilename = data_path+"/routes/all_routes.txt"
        route_file = open(Rfilename, 'r')
        routes = route_file.readlines()

        num_thread = 1000;
        sublist_len = len(routes)/num_thread
        for i in range(0, len(routes), sublist_len):
            subroutes = routes[i:i+sublist_len]
            thread = threading.Thread(target=read_IProute_files_thread, args=(subroutes, initial_routes))
            thread_list.append(thread)

        for thread in thread_list:
            thread.start()
        for thread in thread_list:
            thread.join()

        copy_initial_routes = initial_routes[:]
        constellation_routes = {k: [] for k in range(num_of_satellites)}
        for route in copy_initial_routes:
            current_route = route[0]
            i = current_route[0]
            constellation_routes[i].append(route)

        end = round(time.time()*1000)
        if DEBUG == 1:
            print " Get Initial routes from log files took ", end-start, "ms ", "for ", len(initial_routes), " routes"

    return {
                "All_PreConfigured_routes": initial_routes,
                "Routes_per_satellites": constellation_routes
            }

def prepare_routing_config_commands(topology, data_path, initial_routes, topg, list_of_Intf_IPs, satellites_by_index, num_of_threads):
    start = round(time.time()*1000)
    ipRouteCMD = topology.create_static_routes_batch_parallel(initial_routes, topg["isl_gls_links"], list_of_Intf_IPs, satellites_by_index, num_of_threads)
    logg = open(data_path+"/stat_r.sh", "w")
    for c in ipRouteCMD:
        logg.write(c)
    logg.close()
    end = round(time.time()*1000)
    if DEBUG == 1:
        print " Generate the IP Route commands for the whole constellation took ", end-start, "ms "

    file1 = open(data_path+"/stat_r.sh", 'r')
    Lines = file1.readlines()

    if os.path.isdir(data_path+"/cmd_files") == False:
        os.mkdir(data_path+"/cmd_files")

    for f in os.listdir(data_path+"/cmd_files"):
        os.remove(os.path.join(data_path+"/cmd_files", f))

    count = 0
    for line in Lines:
        command = line.strip().split(" ")
        file = open(data_path+"/cmd_files/"+command[0]+"_routes.sh", 'a')
        string_to_write = ""
        for i in range(1,len(command)):
            string_to_write += command[i]+" "

        file.writelines(string_to_write+"\n")
        file.close()

def dump_ALL(data_path, current_time, links, m_intfs, satellites_by_index, satellites_by_name, routes, GS_SAT_Table):
    time_log = open(data_path+"/time_log.txt", "w")
    links_log = open(data_path+"/links_log.txt", "w")
    m_intf_log = open(data_path+"/m_intf_log.txt", "w")
    satellitesInd_log = open(data_path+"/satellites_by_index_log.txt", "w")
    satellitesName_log = open(data_path+"/satellites_by_name_log.txt", "w")

#### Log Time
    time_log.write(current_time + "\n")
#### Log links
    for link in links:
        links_log.write(link + "\n")
    links_log.close()
#### Log management interfaces -- That is not used now
    for intf in m_intfs:
        m_intf_log.write(intf["node"] + "\t" + intf["mgnt_ip"] + "\n")
    m_intf_log.close()
#### Log satellites by index
    for sat in satellites_by_index:
        satellitesInd_log.write(str(sat) + "\n")
    satellitesInd_log.close()
#### Log satellites name accourding to Starlink (STARLINKXXXX)
    for sat in satellites_by_name:
        satellitesName_log.write(str(sat) + "\n")
    satellitesName_log.close()
#### Log initial routes
    os.mkdir(data_path+"/routes")
    for route in routes:
        current_route = route[0][:]
        routes_log = open(data_path+"/routes/all_routes.txt", "a")
        routes_log.write(str(current_route)[1:-1] + "\n")
        routes_log.close()

    for route in routes:
        if len(route[0]) > 2:
            current_route = route[0][:]
            src_node, next_hop_node, dest_node, last_hop_node = current_route[0], current_route[1], current_route[len(current_route)-1], current_route[len(current_route)-2]
            src_node = "sat"+str(src_node) if src_node < len(satellites_by_index) else "gs"+str(src_node%len(satellites_by_index))
            dest_node = "sat"+str(dest_node) if dest_node < len(satellites_by_index) else "gs"+str(dest_node%len(satellites_by_index))
            routes_log = open(data_path+"/routes/"+str(src_node)+"_routes.txt", "a")
            routes_log.write(str(current_route)[1:-1] + "\n")
            routes_log.close()

            routes_log = open(data_path+"/routes/"+str(dest_node)+"_routes.txt", "a")
            current_route.reverse()
            routes_log.write(str(current_route)[1:-1] + "\n")
            routes_log.close()

        elif len(route[0]) == 2:
            current_route = route[0][:]
            src_node, next_hop_node, dest_node, last_hop_node = current_route[0], current_route[1], current_route[len(current_route)-1], current_route[len(current_route)-1]
            src_node = "sat"+str(src_node) if src_node < len(satellites_by_index) else "gs"+str(src_node%len(satellites_by_index))
            dest_node = "sat"+str(dest_node) if dest_node < len(satellites_by_index) else "gs"+str(dest_node%len(satellites_by_index))
            routes_log = open(data_path+"/routes/"+str(src_node)+"_routes.txt", "a")
            routes_log.write(str(current_route)[1:-1] + "\n")
            routes_log.close()

            routes_log = open(data_path+"/routes/"+str(dest_node)+"_routes.txt", "a")
            current_route.reverse()
            routes_log.write(str(current_route)[1:-1] + "\n")
            routes_log.close()
#### Log Ground station - Satellite Table -- That is not used now
    for index, gs_sat in enumerate(GS_SAT_Table):
        gs_sat_log = open(data_path+"/GS_SAT_Table.txt", "a")
        if len(gs_sat) > 0:
            gs_sat_log.write(str(index)+"\t"+str(gs_sat)[1:-1] + "\n")

        gs_sat_log.close()

    print("..... ALL data is Logged!\n")

def get_time(filename):
    file = open(filename, 'r')
    lines = file.readlines()
    used_time = lines[0]

    year, month, day, hour, minute, newscs = used_time.split(",")
    ts = load.timescale()
    t = ts.utc(int(year), int(month), int(day), int(hour), int(minute), float(newscs))
    print t.tt

    return {"tt": t,
            "year": year,
            "month": month,
            "day": day,
            "hour": hour,
            "minutes": minute,
            "newscs": newscs
        }

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


def main():

    mode = TestbedMode.SWPLUSHW.value

    if mode == TestbedMode.SWPLUSHW.value:
        number_of_hw_sats = 1
        number_of_hw_gs = 1
        number_of_hw_nodes = number_of_hw_sats + number_of_hw_gs


    FreshRun = True
    SimulationTime_secs = 20
    Step_secs = 1

    actual_time = 0
    loggedTime = ""
    data_timestamp = "2022,03,16,11,29,36.124013"
    data_path = "../data_gen/archieved_data_"+str(data_timestamp)

    N = 3
    number_of_orbits = 72

    if FreshRun == True:
        ts = load.timescale()
        actual_time = ts.now()

        dt, leap_second = actual_time.utc_datetime_and_leap_second()
        newscs = ((str(dt).split(" ")[1]).split(":")[2]).split("+")[0]
        date, timeN, zone = actual_time.utc_strftime().split(" ")
        year, month, day = date.split("-")
        hour, minute, second = timeN.split(":")
        loggedTime = str(year)+","+str(month)+","+str(day)+","+str(hour)+","+str(minute)+","+str(newscs)
        if DEBUG == 1:
            print " The Actual real time for the simulation is ", loggedTime

        data_path = "../data_gen/archieved_data_"+str(loggedTime)
        os.mkdir(data_path)

        tle_url = "https://celestrak.com/NORAD/elements/supplemental/starlink.txt"
        tle_file = wget.download(tle_url, out = data_path)
        ground_stations = read_gs("../mobility/ground_stations.txt")

        if mode == TestbedMode.SWPLUSHW.value:
            ground_stations_phys_index = []
            for gs in ground_stations:
                if gs["type"] == 1:
                    ground_stations_phys_index.append(gs["gid"])


        satellites = load.tle_file("https://celestrak.com/NORAD/elements/supplemental/starlink.txt")

        satellites_by_name = {sat.name.split(" ")[0]: sat for sat in satellites}
        satellites_by_index = {}

        if mode == TestbedMode.SWPLUSHW.value:
            satellites_phys_index = []
            satellites_phys = []
            for i in range(number_of_hw_sats):
                satellites_phys.append(satellites_by_name.items()[i])
                print "Satellite ", satellites_by_name.items()[i], " is a physical sateellite "

        orbital_data = get_orbital_planes_classifications(data_path+"/starlink.txt",1)

    elif FreshRun == False:
        ground_stations = read_gs("../mobility/ground_stations.txt")

        if mode == TestbedMode.SWPLUSHW.value:
            ground_stations_phys_index = []
            for gs in ground_stations:
                if gs["type"] == 1:
                    ground_stations_phys_index.append(gs["gid"])

        satellites = load.tle_file("https://celestrak.com/NORAD/elements/supplemental/starlink.txt")

        satellites_by_name_from_file = get_sats_by_name(data_path+"/satellites_by_name_log.txt")
        satellites_by_name = {sat.name.split(" ")[0]: sat for sat in satellites if sat.name.split(" ")[0] in satellites_by_name_from_file}
        satellites_by_index = {}

        if mode == TestbedMode.SWPLUSHW.value:
            satellites_phys_index = []
            satellites_phys = []
            for i in range(number_of_hw_sats):
                satellites_phys.append(satellites_by_name.items()[i])
                print "Satellite ", satellites_by_name.items()[i], " is a physical sateellite "

        orbital_data = get_orbital_planes_classifications(data_path+"/starlink.txt",1)

        actual_time = get_time(data_path+"/time_log.txt")
        if DEBUG == 1:
            print " The Actual real time for the simulation is ", actual_time["tt"].utc_strftime()

# [[Orbital Data]] Sort the satellites in the orbit. We need that in order to know the adjacent satellites
# in the same orbit.
    satellites_sorted_in_orbits = []        #carry satellites names according to STARLINK naming conversion (list of lists)
    for i in range(number_of_orbits):
        satellites_in_orbit = []
        cn = 0
        for data in orbital_data:
            if i == int(orbital_data[str(data)][2]):
                satellites_in_orbit.append(satellites_by_name[str(data.split(" ")[0])])
                if DEBUG == 1:
                    print i, data, orbital_data[str(data)]
                cn +=1
        if DEBUG == 1:
            print "Orbit no.", i, "num of satellites ", cn

        if FreshRun == False:
            satellites_sorted_in_orbits.append(sort_satellites_in_orbit(satellites_in_orbit, actual_time["tt"]))
        elif FreshRun == True:
            satellites_sorted_in_orbits.append(sort_satellites_in_orbit(satellites_in_orbit, actual_time))

# Update the satellite_by_index
    sat_index = -1
    for orbit in satellites_sorted_in_orbits:
        for i in range(len(orbit)):
            sat_index += 1
            satellites_by_index[sat_index] = orbit[i].name.split(" ")[0]

            if mode == TestbedMode.SWPLUSHW.value:
                for phys in satellites_phys:
                    if orbit[i].name.split(" ")[0] in phys[0]:
                        satellites_phys_index.append(sat_index)
                        print "Satellite ", orbit[i].name.split(" ")[0], " is a physical satellite and its index = ", sat_index
####
    num_of_satellites = len(orbital_data)
    num_of_ground_stations = len(ground_stations)
    if DEBUG == 1:
        print "total number of satellites = ", num_of_satellites
        print "total number of ground_stations = ", num_of_ground_stations

# [[Build Topology and Links]] Build the network topology, specifically, the Inter-Satellites-Links (mininet_add_ISLs) and GroundStation-Satellites-Links (mininet_add_GSLs)
# Compute links charateristics in terms of latency, bandwidth and snr
    GS_SAT_Table = [[] for i in range(num_of_satellites)]
    conn_mat_size = num_of_satellites + num_of_ground_stations
    connectivity_matrix = [[0 for c in range(conn_mat_size)] for r in range(conn_mat_size)]
    if FreshRun == False:
        connectivity_matrix = mininet_add_ISLs(connectivity_matrix, satellites_sorted_in_orbits, satellites_by_name, satellites_by_index, "SAME_ORBIT_AND_GRID_ACROSS_ORBITS", actual_time["tt"])
        connectivity_matrix = mininet_add_GSLs(connectivity_matrix, satellites_by_name, satellites_by_index, ground_stations, 12, "BASED_ON_DISTANCE_ONLY_MININET", actual_time["tt"], 1, GS_SAT_Table)
    elif FreshRun == True:
        connectivity_matrix = mininet_add_ISLs(connectivity_matrix, satellites_sorted_in_orbits, satellites_by_name, satellites_by_index, "SAME_ORBIT_AND_GRID_ACROSS_ORBITS", actual_time)
        connectivity_matrix = mininet_add_GSLs(connectivity_matrix, satellites_by_name, satellites_by_index, ground_stations, 12, "BASED_ON_DISTANCE_ONLY_MININET", actual_time, 1, GS_SAT_Table)

    gs_statellite_pair = get_gs_sat_pairs(connectivity_matrix, num_of_satellites)
    # print gs_statellite_pair
    # exit()
    if FreshRun == False:
        links_charateristics = calculate_link_charateristics_for_gsls_isls(connectivity_matrix, satellites_by_index, satellites_by_name, ground_stations, actual_time["tt"])
    elif FreshRun == True:
        links_charateristics = calculate_link_charateristics_for_gsls_isls(connectivity_matrix, satellites_by_index, satellites_by_name, ground_stations, actual_time)

    available_ips = generate_ips_for_constellation()
    available_ips_phys = generate_ips_for_physical_nodes(10)
    if DEBUG == 1:
        print "..... Finished the Build Topology part"
####
# [[Routing and Mininet]] Compute the all the routes to all nodes in the topology. We need these routes before we go into mininet to do initial routing table configuration
# for all nodes in Mininet. We then pass these info to Mininet to create the topology there
    TopologyRoutes = get_topology_routes(FreshRun, data_path, num_of_satellites, satellites_by_index, ground_stations, connectivity_matrix, links_charateristics)
    # print len(TopologyRoutes["All_PreConfigured_routes"])
    topology = sat_network(N=N)
    updates_files_name = ["2022-02-24 11:51:59 UTC_.txt", "2022-02-24 11:52:00 UTC_.txt", "2022-02-24 11:52:01 UTC_.txt", "2022-02-24 11:52:02 UTC_.txt"]

    topg = topology.create_sat_network(satellites=satellites_by_index, ground_stations=ground_stations, connectivity_matrix=connectivity_matrix, link_throughput=links_charateristics["throughput_matrix"], link_latency=links_charateristics["latency_matrix"], Tmode=mode, physical_gs_index=ground_stations_phys_index, physical_sats_index=satellites_phys_index)
    net = Mininet(topo = topology, link=TCLink, autoSetMacs = True)
    #topology.updateRoutingTables_timer(Step_secs, data_path, net, updates_files_name, num_of_satellites, 0)
    net.start()
    list_of_Intf_IPs = topology.initial_ipv4_assignment_for_interfaces(data_path, net, available_ips, available_ips_phys)
    if FreshRun == True:
        dump_ALL(data_path, loggedTime, topg["isl_gls_links"], topg["management_interface"], satellites_by_index, satellites_by_name, TopologyRoutes["All_PreConfigured_routes"], GS_SAT_Table)

    prepare_routing_config_commands(topology, data_path, TopologyRoutes["All_PreConfigured_routes"], topg, list_of_Intf_IPs, satellites_by_index, 20);
    start = round(time.time()*1000)
    gs_routing(data_path, gs_statellite_pair, topg["isl_gls_links"], num_of_satellites, satellites_by_index, list_of_Intf_IPs, TopologyRoutes["Routes_per_satellites"])
    end = round(time.time()*1000)
    if DEBUG == 1:
        print " GS Routing took ", end-start, "ms "
    # exit()
    start = round(time.time()*1000)
    topology.startRoutingConfigV2(data_path,net, satellites_by_index, ground_stations, topg["management_interface"])
    end = round(time.time()*1000)
    if DEBUG == 1:
        print " Deploy the IP Route commands for whole constellation took ", end-start, "ms "
####
    # CLI(net)
    # net.stop()
    # dump_ALL(data_path, loggedTime, topg["isl_gls_links"], topg["management_interface"], satellites_by_index, satellites_by_name, TopologyRoutes["All_PreConfigured_routes"], GS_SAT_Table)
    #exit()
####

####
# [[Iterative Simulation]] Now we compute the changes in the topology ever Step_secs and store that.
#
    addthis = 0
    links_updated = topg["isl_gls_links"][:]
    last_CMatrix = []
    updates_files_name = []
    while SimulationTime_secs > 0:
        start1 = round(time.time()*1000)
        SimulationTime_secs -= Step_secs
        addthis += Step_secs

        if FreshRun == True:
            actual_time = get_time(data_path+"/time_log.txt")

        ts = load.timescale()
        actual_time_increment = ts.utc(int(actual_time["year"]), int(actual_time["month"]), int(actual_time["day"]), int(actual_time["hour"]), int(actual_time["minutes"]), float(actual_time["newscs"])+addthis)
        print actual_time_increment.utc_strftime()

        new_GS_SAT_Table = [[] for i in range(num_of_satellites)]
        new_CMatrix = [[0 for c in range(conn_mat_size)] for r in range(conn_mat_size)]

        start = round(time.time()*1000)
        new_CMatrix = mininet_add_ISLs(new_CMatrix, satellites_sorted_in_orbits, satellites_by_name, satellites_by_index, "SAME_ORBIT_AND_GRID_ACROSS_ORBITS", actual_time_increment)
        new_CMatrix = mininet_add_GSLs(new_CMatrix, satellites_by_name, satellites_by_index, ground_stations, 12, "BASED_ON_DISTANCE_ONLY_MININET", actual_time_increment, 1, new_GS_SAT_Table)
        end = round(time.time()*1000)

        print " Re calculate the ISL and GSL links took ", end-start, "ms "

        if len(last_CMatrix) > 0:
            route_changes = check_changes_in_routes(last_CMatrix, new_CMatrix)

            print " at ", actual_time_increment.utc_strftime(), "there are ", len(route_changes), " route changes"
            updates_files_name.append(str(actual_time_increment.utc_strftime())+"_.txt")
            if len(route_changes) < 400:
                lightweight_routing(data_path, route_changes, links_updated, num_of_satellites, satellites_by_index, list_of_Intf_IPs, TopologyRoutes["Routes_per_satellites"], actual_time_increment)
                # we need to update links_updated
        last_CMatrix = new_CMatrix[:]
        end1 = round(time.time()*1000)
        print " Route update iteration took  ", (end1-start1), "ms "
    # CLI(net)
    # net.stop()
    # exit()
####
####

    thread_performance = threading.Thread(target=ping_thread, args=(net,))
    thread_performance.start()
    #
    updates_files_name = []
    for fileLog in os.listdir(data_path):
        if fileLog.startswith("allchanges_log"):
            a = re.split('_| ',fileLog)
            filesd = a[2]+" "+a[3]+" "+a[4]
            updates_files_name.append(filesd)

    updates_files_name.sort()

    time_counter = 0
    for file in updates_files_name:
        if time_counter > SimulationTime_secs:
            exit()

        st = round(time.time() * 1000)
        print "[ %0.12f" % round(time.time() * 1000),"] Start --> ", file
        net = update_loop(data_path, net, file, num_of_satellites);
        print "[ %0.12f" % round(time.time() * 1000),"] End   --> ", file
        time_counter += 1

    exit()
####
#####

setLogLevel('info')    # 'info' is normal; 'debug' is for when there are problems
main()
