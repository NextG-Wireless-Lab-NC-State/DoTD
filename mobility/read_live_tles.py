from skyfield.api import N, W, wgs84, load, EarthSatellite
from multiprocessing import Process, Manager, Pool
import time
import networkx as nx
import matplotlib.pyplot as plt
import bellmanford as bf
import itertools
import copy
import collections
import math
import wget
import os


import sys
from mobility_utils import *

def get_orbital_planes(tle_filename, shell_num):
    orbital_data = {}
    tle_file = open(tle_filename, 'r')
    Lines = tle_file.readlines()

    # each iteration we read three lines at once
    for i in range(0,len(Lines),3):
        tle_second_line = list(filter(None, Lines[i+2].strip("\n").split(" ")))

        if shell_num == 1:
            if float(tle_second_line[2]) < 53.2: #Inclination of shell 1 should be 53.0 degrees
                orbital_num = math.floor(float(tle_second_line[3])/5.0)
                orbital_data[Lines[i].strip()] = (tle_second_line[2], tle_second_line[3], orbital_num) #Satellite name: (Inclination, Longitude of the ascending node, orbital number)
                
    return orbital_data

def sort_satellites_in_orbit(satellites_in_orbit, t):
    visited_sats = []
    sorted_sats = []

    first_sat = satellites_in_orbit[0]
    sorted_sats.append(first_sat)
    visited_sats.append(first_sat.name)

    for i in range(len(satellites_in_orbit)):
        next_hop = -1
        min_distance = 1000000000000000
        for sat in satellites_in_orbit:
            if sat.name not in visited_sats:
                distance = distance_between_two_satellites(first_sat, sat,t)
                if distance < min_distance:
                    next_hop = sat
                    min_distance = distance

        if next_hop != -1:
            first_sat = next_hop
            visited_sats.append(first_sat.name)
            sorted_sats.append(first_sat)

    return sorted_sats

def main():
    satellites = load.tle_file("https://celestrak.com/NORAD/elements/starlink.txt")
    satellites_by_name = {sat.name: sat for sat in satellites}

    if os.path.isfile("./starlink.txt"):
        os.remove("./starlink.txt")

    tle_url = "https://celestrak.com/NORAD/elements/supplemental/starlink.txt"
    tle_file = wget.download(tle_url)

    orbital_data = get_orbital_planes("starlink.txt",1)
    number_of_orbits = 72

    ts = load.timescale()
    t = ts.now()

    satellites_sorted_in_orbits = []
    for i in range(number_of_orbits):
        satellites_in_orbit = []
        for data in orbital_data:
            if i == int(data.values()[0][2]):
                satellites_in_orbit.append(satellites_by_name[str(data.keys()[0])])

        satellites_sorted_in_orbits.append(sort_satellites_in_orbit(satellites_in_orbit, t))

    satellites_by_index = []
    sat_index = -1
    for orbit in satellites_sorted_in_orbits:
        for i in range(len(orbit)):
            sat_index += 1
            satellites_by_index.append({sat_index: orbit[i]})
            print sat_index, orbit[i].name

    print satellites_by_index
# main()
