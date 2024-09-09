import matplotlib.pyplot as plt
import numpy as np


def find_idx_sat(sat_name, satellites_by_index):

    for tmp in range(len(satellites_by_index)):

        if satellites_by_index[tmp] == sat_name:
            return tmp
        
    return -1


def find_idx_in_sorted(idx, satellites_sorted_in_orbits):
    
    orbits = len(satellites_sorted_in_orbits)
    sats_in_orbit = len(satellites_sorted_in_orbits[0])
    
    for orbit in range(orbits):
        for sat in range(sats_in_orbit):
            if idx == satellites_sorted_in_orbits[orbit][sat].name:
                return (orbit, sat)
    
    return (-1, -1)

def find_adj_sats(sat, links, satellites_by_index, satellites_sorted_in_orbits):

    links_p = []
    for (a, b) in links:
        if a[0] == 'g' or b[0] == 'g':
            continue
        a_idx = int(a[3:])
        b_idx = int(b[3:])
        links_p.append((a_idx, b_idx))

    sat_idx = find_idx_sat(sat.name, satellites_by_index)

    result = []
    for (a, b) in links_p:

        if a == sat_idx:
            result.append(find_idx_in_sorted(satellites_by_index[b], satellites_sorted_in_orbits))

        # if b == sat_idx:
        #     result.append(find_idx_in_sorted(satellites_by_index[a], satellites_sorted_in_orbits))


    return result

def distance_between_two_satellites(satellite1, satellite2, t):
    
    position1 = satellite1.at(t)
    position2 = satellite2.at(t)
    
    difference = position2 - position1
    distance = difference.distance().m
    
    return distance

def find_closest_sat_in_set(origin_sat, sats_in_set, t):

    nearest_sat = -1
    min_distance = 1000000000000000

    # Iterate through satellites in the adjacent plane
    for i in range(len(sats_in_set)):
        # Calculate the distance between the original satellite and the current satellite in the adjacent plane
        distance = distance_between_two_satellites(origin_sat, sats_in_set[i], t)

        # Check if the calculated distance is smaller than both the current minimum distance and a threshold value
        if distance < min_distance and distance < 9006000:
            min_distance = distance # update the minimum distance
            nearest_sat = sats_in_set[i] # set the current adj. plane sat as the nearest to the original sat

    # Return the name of the nearest satellite in the adjacent plane
    return nearest_sat

class SatPoint():

    def __init__(self, x, y, orbit):
        self.x = x
        self.y = y
        self.sat = None
        self.adj_sats = []
        self.orbit = orbit

def visualize(arranged_sats, links, time_utc_inc):

    fig, ax = plt.subplots(figsize=(8, 6))

    # Get the DPI value
    dpi = fig.dpi

    # Calculate size in pixels
    width = int(fig.get_figwidth() * dpi)
    height = int(fig.get_figheight() * dpi)

    links_p = []
    for link in links:
        endpoint1, endpoint2  = link.split(":")
        endpoint1, endpoint2 = str(endpoint1.split("-")[0]), str(endpoint2.split("-")[0])
        links_p.append((endpoint1, endpoint2))


    satellites_by_index         = arranged_sats["satellites by index"]
    satellites_sorted_in_orbits = arranged_sats["sorted satellite in orbits"]

    n_orbits = len(satellites_sorted_in_orbits)
    n_sats_in_orbit = len(satellites_sorted_in_orbits[0])

    horizontal_dist_orbits = width / n_orbits
    orbits_center_x = (np.array(range(n_orbits)) + 0.5) * horizontal_dist_orbits

    vertical_dist_orbits = height / n_sats_in_orbit
    orbits_center_y = (np.array(range(n_sats_in_orbit)) + 0.5) * vertical_dist_orbits

    sat_points = []

    for orbit in range(n_orbits):
        sat_points.append([])
        for sat in range(n_sats_in_orbit):
            sat_points[orbit].append(SatPoint(orbits_center_x[orbit], orbits_center_y[sat], orbit))

    # randomly start from a satellite in orbit 0:
    rnd_orbit = 4
    rnd_sat_in_orbit = 3
    sat_points[rnd_orbit][rnd_sat_in_orbit].sat = satellites_sorted_in_orbits[rnd_orbit][rnd_sat_in_orbit]

    adj_sats_4_0_idx = find_adj_sats(sat_points[rnd_orbit][rnd_sat_in_orbit].sat, links_p, satellites_by_index, satellites_sorted_in_orbits)
    sat_points[rnd_orbit][rnd_sat_in_orbit].adj_sats = adj_sats_4_0_idx



    # plot sats in orbits
    for orbit in sat_points:
        for sat_point in orbit:
            ax.plot(sat_point.x, sat_point.y, 'o', color='y')

    # plot links
    for orbit in sat_points:
        for sat_point in orbit:
            for adj_sat in sat_point.adj_sats:
                ax.plot((sat_point.x, sat_points[adj_sat[0]][adj_sat[1]].x), (sat_point.y, sat_points[adj_sat[0]][adj_sat[1]].y))

    plt.show()