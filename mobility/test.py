import networkx as nx
import sys
from read_real_tles import *
from mobility_utils import *

satellites = load.tle_file("https://celestrak.com/NORAD/elements/starlink.txt")
satellites_by_name = {sat.name: sat for sat in satellites}
planes = extract_planes("starlink_tles.txt")

cur_planes = planes["Planes"]
print len(planes["Unassigned"])
ts = load.timescale()
t = ts.now()

sorted_planes = sort_satellites_within_plane(cur_planes, satellites_by_name, t)

# 
# num_of_satellites = 0;
# available_satellites = []
# for key in sorted_planes.keys():
#     sats = ""
#     for satellite in sorted_planes[key]:
#         sats += str(satellites_by_name[str(satellite)].name).split("-")[1]+","
#         available_satellites.append(satellites_by_name[str(satellite)])
#
# available_satellites_by_name = {sat.name: sat for sat in available_satellites}
#
# sorted_by_key = label_satellites_properly(sorted_planes, len(available_satellites_by_name))
# print(sorted_by_key)

# # print len(available_satellites)
#
# G = nx.Graph()
# for sat in available_satellites:
#     G.add_node(sat.name)
#
# G = graph_add_ISLs(G, available_satellites_by_name, sorted_planes, 0, 0, "SAME_ORBIT_AND_BASED_ON_DISTANCE_FOR_INTER_ORBIT", t)
