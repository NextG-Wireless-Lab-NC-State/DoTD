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



class LinuxRouter( Node ):	# from the Mininet library
    "A Node with IP forwarding enabled."

    def config( self, **params ):
        super( LinuxRouter, self).config( **params )
        # Enable forwarding on the router
        info ('enabling forwarding on ', self)
        self.cmd( 'sysctl net.ipv4.ip_forward=1' )

    def terminate( self ):
        self.cmd( 'sysctl net.ipv4.ip_forward=0' )
        super( LinuxRouter, self ).terminate()


class sat_network(Topo):
    def __init__(self, **kwargs):
        super(sat_network, self).__init__(**kwargs)

    def rp_disable(self, host):
    	ifaces = host.cmd('ls /proc/sys/net/ipv4/conf')
    	ifacelist = ifaces.split()    # default is to split on whitespace
    	for iface in ifacelist:
		if iface != 'lo': host.cmd('sysctl net.ipv4.conf.' + iface + '.rp_filter=0')

    def set_default_gw_gs(self, net, gs_list):
        for gs in gs_list:
            ground_station = net.getNodeByName(gs)
            print ground_station.IP()


    def create_sat_network(self, satellites, ground_stations, connectivity_matrix):
        sat_list = []
        gs_list  = []
        links    = []

        sat_intf_count = []
        sat_intf_count = [0 for i in range(len(satellites))]

        for i in range(0, len(satellites)):
            sat_name = self.addHost('sat'+str(i), cls=LinuxRouter)
            sat_list.append(sat_name)

        for i in range(0, len(ground_stations)):
            gs_name = self.addHost('gs'+str(i))
            gs_list.append(gs_name)

        connectivity_matrix_temp = connectivity_matrix
        for i in range(0,len(connectivity_matrix_temp)):
            for j in range(0, len(connectivity_matrix_temp[i])):
                # Add the ISL links
                if i < len(satellites) and j < len(satellites) and connectivity_matrix_temp[i][j] == 1:
                    self.addLink(sat_list[i], sat_list[j], intfname1 = 'sat'+str(i)+'-eth'+str(sat_intf_count[i]), inftname2 = 'sat'+str(j)+'-eth'+str(sat_intf_count[j]), cls=TCLink)
                    links.append('sat'+str(i)+'-eth'+str(sat_intf_count[i])+":"+'sat'+str(j)+'-eth'+str(sat_intf_count[j]))

                    connectivity_matrix_temp[i][j] = 0
                    connectivity_matrix_temp[j][i] = 0

                    sat_intf_count[i] = sat_intf_count[i] + 1
                    sat_intf_count[j] = sat_intf_count[j] + 1

                # Add the GSL links
                if i < len(satellites) and j >= len(satellites) and connectivity_matrix_temp[i][j] == 1:
                    gid = j - len(satellites)
                    self.addLink(sat_list[i], gs_list[gid], intfname1 = 'sat'+str(i)+'-eth'+str(sat_intf_count[i]), inftname2 = 'gs'+str(gid)+'-eth0', cls=TCLink)
                    links.append('sat'+str(i)+'-eth'+str(sat_intf_count[i])+":"+ 'gs'+str(gid)+'-eth0')

                    connectivity_matrix_temp[i][j] = 0
                    connectivity_matrix_temp[j][i] = 0

                    sat_intf_count[i] = sat_intf_count[i] + 1

        return {
        	"sat_list": sat_list,
        	"gs_list": gs_list,
            "links": links,
            "intf_count_sats": sat_intf_count
    	}

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

    net = Mininet(topo = topology, link=TCLink, autoSetMacs = True)
    net.start()
    CLI( net)
    net.stop()

    os.system("killall -9 ospfd zebra")
    os.system("rm -f /tmp/*.pid")

setLogLevel('info')    # 'info' is normal; 'debug' is for when there are problems
main()
