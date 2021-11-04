from skyfield.api import N, W, wgs84, load, EarthSatellite
from multiprocessing import Process, Manager, Pool
import time
import networkx as nx
import matplotlib.pyplot as plt
import bellmanford as bf
import itertools
import copy
import collections

import sys
from mobility_utils import *

def extract_planes(str_filename):
	unassigned_satellites = []
	starlink_planes = {'2' : [], '7' : [], '12' : [], '17' : [], '22' : [], '27' : [], '32' : [], '37' : [], '42' : [], '47' : [], '52' : [],'57' : [],
	'62' : [], '67' : [], '72' : [], '77' : [], '82' : [], '87' : [], '92' : [], '97' : [], '102' : [], '107' : [], '112' : [], '117' : [],
	'122' : [], '127' : [], '132' : [], '137' : [], '142' : [], '147' : [], '152' : [], '157' : [], '162' : [], '167' : [], '172' : [], '177' : [],
	'182' : [], '187' : [], '192' : [], '197' : [], '202' : [], '207' : [], '212' : [], '217' : [], '222' : [], '227' : [], '232' : [], '237' : [],
	'242' : [], '247' : [], '252' : [], '257' : [], '262' : [], '267' : [], '272' : [], '277' : [], '282' : [], '287' : [], '292' : [], '297' : [],
	'302' : [], '307' : [], '312' : [], '317' : [], '322' : [], '327' : [], '332' : [], '337' : [], '342' : [], '347' : [], '352' : [], '357' : []
	}
	tle_file = open(str_filename, 'r')
	Lines = tle_file.readlines()

	for i in range(0,len(Lines),3):
		tle_second_line = []
		# print Lines[i].strip("\n").strip(), Lines[i+2].strip("\n")
		for val in Lines[i+2].strip("\n").split(" "):
			if val != "":
				tle_second_line.append(val)

		Long_of_the_ascending_node = int(round(float(tle_second_line[3])))
		vals = Lines[i].strip("\n").strip()
		# vals = (Lines[i].strip("\n").strip(), Lines[i+2].strip("\n"))
		if str(Long_of_the_ascending_node) in starlink_planes.keys():
			if "VISORSAT" not in vals:
				starlink_planes[str(Long_of_the_ascending_node)].append(vals)
		else:
			if "VISORSAT" not in vals:
				# print vals
				unassigned_satellites.append({"sat": vals, "Long_of_the_ascending_node": Long_of_the_ascending_node})

	return {
			"Planes": starlink_planes,
			"Unassigned": unassigned_satellites
			}

def sort_satellites_within_plane(cur_planes, satellites_by_name, t):
	for value in cur_planes.keys():
		visited_sats = []
		first_sat = satellites_by_name[str(cur_planes[value][0])]
		visited_sats.append(first_sat.name)
		for i in range(1,len(cur_planes[value])):
			min_dist = 1000000000000000
			next_hop = -1
			for sats in cur_planes[value]:
				next_sat = satellites_by_name[str(sats)]
				if next_sat.name not in visited_sats:
					min_d = distance_between_two_satellites(first_sat, next_sat,t)
					if min_d < min_dist:
						next_hop = next_sat
						min_dist = min_d

			if next_hop != -1:
				# print first_sat, next_hop, min_dist
				first_sat = next_hop
				visited_sats.append(first_sat.name)

		cur_planes[value] = visited_sats
	return cur_planes

def resolve_unassigned_satellites(unassigned_satellites, current_planes, satellites, t):
	for sat in unassigned_satellites:
		minimum_with_a_plane = 1000000000000000
		same_plane_count = 0
		belong_plane = -1
		if (sat["Long_of_the_ascending_node"] != 355) and (sat["Long_of_the_ascending_node"] != 356) and (sat["Long_of_the_ascending_node"] != 354):
			for key in current_planes:
				for sat_in_plane in current_planes[key]:
					# min_distance = abs(int(sat["Long_of_the_ascending_node"]) - int(key))
					min_distance = distance_between_two_satellites(satellites[sat["sat"]], satellites[sat_in_plane],t)
					# print sat, key, min_distance
					if min_distance < minimum_with_a_plane:
						minimum_with_a_plane = min_distance
						belong_plane = key

			current_planes[belong_plane].append(sat["sat"])
			print sat, belong_plane, minimum_with_a_plane

	return current_planes

def label_satellites_properly(sorted_planes_by_values, num_of_satellites):
	starlink_planes = {2 : [], 7 : [], 12 : [], 17 : [], 22 : [], 27 : [], 32 : [], 37 : [], 42 : [], 47 : [], 52 : [],57 : [],
	62 : [], 67 : [], 72 : [], 77 : [], 82 : [], 87 : [], 92 : [], 97 : [], 102 : [], 107 : [], 112 : [], 117 : [],
	122 : [], 127 : [], 132 : [], 137 : [], 142 : [], 147 : [], 152 : [], 157 : [], 162 : [], 167 : [], 172 : [], 177 : [],
	182 : [], 187 : [], 192 : [], 197 : [], 202 : [], 207 : [], 212 : [], 217 : [], 222 : [], 227 : [], 232 : [], 237 : [],
	242 : [], 247 : [], 252 : [], 257 : [], 262 : [], 267 : [], 272 : [], 277 : [], 282 : [], 287 : [], 292 : [], 297 : [],
	302 : [], 307 : [], 312 : [], 317 : [], 322 : [], 327 : [], 332 : [], 337 : [], 342 : [], 347 : [], 352 : [], 357 : []
	}
	count = 0
	actual_sat_number_to_counter = [0 for s in range(num_of_satellites)]
	for s_key in sorted(starlink_planes.keys()):
		for values in sorted_planes_by_values[str(s_key)]:
			starlink_planes[s_key].append(count)
			actual_sat_number_to_counter[count] = values
			count += 1

	for v in range(len(actual_sat_number_to_counter)):
		print v, actual_sat_number_to_counter[v]

	return actual_sat_number_to_counter
#
# satellites = load.tle_file("https://celestrak.com/NORAD/elements/starlink.txt")
# satellites_by_name = {sat.name: sat for sat in satellites}
# planes = extract_planes("starlink_tles.txt")
# #
# cur_planes = planes["Planes"]
# print len(planes["Unassigned"])
# ts = load.timescale()
# t = ts.now()
#
# sorted_planes = sort_satellites_within_plane(cur_planes, satellites_by_name, t)
# for keys in sorted_planes.keys():
# 	print keys
# 	for values in sorted_planes[keys]:
# 		print values

# for val in planes["Planes"].keys():
# 	print val
# 	for a in planes["Planes"][val]:
# 		print a
# ts = load.timescale()
# t = ts.now()
# current_planes = resolve_unassigned_satellites(planes["Unassigned"], planes["Planes"], satellites_by_name, t)

# for val in current_planes.keys():
# 	print val, len(current_planes[val])
# 	# for sat in current_planes[val]:
# 	# 	print sat
