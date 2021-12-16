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

def main():
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
    actual_sat_number_to_counter = label_satellites_properly(sorted_planes, len(available_satellites_by_name))

    ground_stations = read_gs("../mobility/ground_stations.txt")

    num_of_satellites = len(available_satellites_by_name)
    num_of_ground_stations = len(ground_stations)
    conn_mat_size = num_of_satellites + num_of_ground_stations

    G = nx.Graph()
    G = graph_add_ISLs(G, available_satellites_by_name, actual_sat_number_to_counter, sorted_planes, 0, 0, "SAME_ORBIT_AND_BASED_ON_DISTANCE_FOR_INTER_ORBIT", t)
    G = graph_add_GSLs(G, available_satellites_by_name, actual_sat_number_to_counter, ground_stations, t, 8, "BASED_ON_DISTANCE_ONLY_GRAPH")

    # for lm in G["GSL_Connectivity"]:
    #     print lm

    print ground_stations[27]
    ts = load.timescale()
    t = ts.now()
    t2 = t.utc_datetime()+datetime.timedelta(0,1)
    while(True):
        t = ts.utc(t2.year, t2.month, t2.day, t2.hour, t2.minute, t2.second)
        old_gsls = G["GSL_Connectivity"][:]
        G = graph_add_GSLs(G["Graph"], available_satellites_by_name, actual_sat_number_to_counter, ground_stations, t, 8, "BASED_ON_DISTANCE_ONLY_GRAPH")
        for i in range(len(G["GSL_Connectivity"])):
            print t.utc_strftime('%Y-%m-%d %H:%M:%S')+"\t"+str(i)+"\t"+str(G["GSL_Connectivity"][i])

        t2 = t.utc_datetime()+datetime.timedelta(0,1)
        # gsls_differences = get_differences_in_GSLs_between_iterations(old_gsls, G["GSL_Connectivity"])
        # print gsls_differences

main()
