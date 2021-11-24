from skyfield.api import N, W, wgs84, load, EarthSatellite
import time
from multiprocessing import Process, Manager, Pool

max_gsl_length_m = 1089686.4181956202;

def calc_distance_gs_sat_worker(args):
    (
    ground_station,
    satellite,
    sid,
    time_t
    ) = args

    ground_station_satellites_in_range = []
    satellites_in_range = []
    distance_m = distance_between_ground_station_satellite(ground_station, satellite, time_t)
    if distance_m <= max_gsl_length_m:
        satellites_in_range.append((distance_m, sid, ground_station["gid"]))

    ground_station_satellites_in_range.append(satellites_in_range)

    return ground_station_satellites_in_range

def distance_between_ground_station_satellite(ground_station, satellite, t):
    bluffton = wgs84.latlon(float(ground_station["latitude_degrees_str"]), float(ground_station["longitude_degrees_str"]))
    geocentric = satellite.at(t)
    difference = satellite - bluffton
    topocentric = difference.at(t)

    alt, az, distance = topocentric.altaz()

    return distance.m

def distance_between_two_satellites(satellite1, satellite2, t):
    position1 = satellite1.at(t)
    position2 = satellite2.at(t)
    difference = position2 - position1

    return (position2 - position1).distance().m

def find_nearest_sat_in_adjacent_plane(constellation_planes, sat, key, satellites_by_name, t):
    adj_sat = []
    adj_planes = [-1, -1]
    adj_planes[0], adj_planes[1] = ((key-5)%360), ((key+5)%360)
    sat1 = satellites_by_name[str(sat)]
    for adj_plane in adj_planes:
        closest_sat = -1
        minimum_distance = 1000000000000000
        for sats in constellation_planes[str(adj_plane)]:
            satx = satellites_by_name[str(sats)]
            distance = distance_between_two_satellites(sat1, satx, t)
            if distance < minimum_distance:
                minimum_distance = distance
                closest_sat = sats

        if closest_sat != -1:
            adj_sat.append(closest_sat)

    return adj_sat

def graph_add_ISLs(G, satellites_by_name, actual_sat_number_to_counter, constellation_planes, n_orbits, n_sats_per_orbit, isl_config, t):
    if isl_config == "SAME_ORBIT_AND_GRID_ON_EDGE_SATELLITES_ONLY":
        for i in range(n_orbits):
            for j in range(n_sats_per_orbit):
                sat = i * n_sats_per_orbit + j

                # Link to the next in the orbit
                sat_same_orbit = i * n_sats_per_orbit + ((j + 1) % n_sats_per_orbit)
                G.add_edge(sat, sat_same_orbit, weight=1)

                # Grid for the edge satellites
                if j % n_sats_per_orbit == 0 or j % (n_sats_per_orbit - 1) == 0:
                    sat_adjacent_orbit = ((i + 1) % n_orbits) * n_sats_per_orbit + (j % n_sats_per_orbit)
                    G.add_edge(sat, sat_adjacent_orbit, weight=1)

    if isl_config == "SAME_ORBIT_AND_BASED_ON_DISTANCE_FOR_INTER_ORBIT":
        for i in range(len(constellation_planes.keys())):
            cur_key = constellation_planes.keys()[i]
            for j in range(len(constellation_planes[str(cur_key)])):

                # In the same plane
                satname, adj_satname = constellation_planes[str(cur_key)][j], constellation_planes[str(cur_key)][(j+1)%len(constellation_planes[str(cur_key)])]
                sat_index = actual_sat_number_to_counter.index(str(satname))
                adj_sat_index = actual_sat_number_to_counter.index(str(adj_satname))
                G.add_edge(sat_index, adj_sat_index, weight=1)

                # In the adjacent planes for the edge sats only.
                if j == 0 or j == len(constellation_planes[str(cur_key)])-1:
                    sat_adjacent_orbit = find_nearest_sat_in_adjacent_plane(constellation_planes, str(satname), int(cur_key), satellites_by_name, t)
                    sat_adjacent_orbit_index1 = actual_sat_number_to_counter.index(str(sat_adjacent_orbit[0]))
                    sat_adjacent_orbit_index2 = actual_sat_number_to_counter.index(str(sat_adjacent_orbit[1]))

                    G.add_edge(sat_index, sat_adjacent_orbit_index1, weight=1)
                    G.add_edge(sat_index, sat_adjacent_orbit_index2, weight=1)
    return G

def mininet_add_ISLs(connectivity_matrix, satellites_by_name, actual_sat_number_to_counter, constellation_planes, n_orbits, n_sats_per_orbit, isl_config, t):
    if isl_config == "SAME_ORBIT_AND_GRID_ON_EDGE_SATELLITES_ONLY":
        for i in range(n_orbits):
            for j in range(n_sats_per_orbit):
                sat = i * n_sats_per_orbit + j

                # Link to the next in the orbit
                sat_same_orbit = i * n_sats_per_orbit + ((j + 1) % n_sats_per_orbit)
                connectivity_matrix[sat][sat_same_orbit] = 1
                connectivity_matrix[sat_same_orbit][sat] = 1

                # Grid for the edge satellites
                if j % n_sats_per_orbit == 0 or j % (n_sats_per_orbit - 1) == 0:
                    sat_adjacent_orbit = ((i + 1) % n_orbits) * n_sats_per_orbit + (j % n_sats_per_orbit)
                    connectivity_matrix[sat][sat_adjacent_orbit] = 1
                    connectivity_matrix[sat_adjacent_orbit][sat] = 1

    if isl_config == "SAME_ORBIT_AND_BASED_ON_DISTANCE_FOR_INTER_ORBIT":
        for i in range(len(constellation_planes.keys())):
            cur_key = constellation_planes.keys()[i]
            for j in range(len(constellation_planes[str(cur_key)])):

                # In the same plane
                satname, adj_satname = constellation_planes[str(cur_key)][j], constellation_planes[str(cur_key)][(j+1)%len(constellation_planes[str(cur_key)])]
                sat_index = actual_sat_number_to_counter.index(str(satname))
                adj_sat_index = actual_sat_number_to_counter.index(str(adj_satname))
                connectivity_matrix[sat_index][adj_sat_index] = 1
                connectivity_matrix[adj_sat_index][sat_index] = 1

                # In the adjacent planes for the edge sats only.
                if j == 0 or j == len(constellation_planes[str(cur_key)])-1:
                    sat_adjacent_orbit = find_nearest_sat_in_adjacent_plane(constellation_planes, str(satname), int(cur_key), satellites_by_name, t)
                    sat_adjacent_orbit_index1 = actual_sat_number_to_counter.index(str(sat_adjacent_orbit[0]))
                    sat_adjacent_orbit_index2 = actual_sat_number_to_counter.index(str(sat_adjacent_orbit[1]))

                    connectivity_matrix[sat_index][sat_adjacent_orbit_index1] = 1
                    connectivity_matrix[sat_adjacent_orbit_index1][sat_index] = 1
                    connectivity_matrix[sat_index][sat_adjacent_orbit_index2] = 1
                    connectivity_matrix[sat_adjacent_orbit_index2][sat_index] = 1

    return connectivity_matrix

def graph_add_GSLs(G, connectivity_matrix, satellites, ground_stations, t, number_of_threads, association_criteria):
    # find all satellites in range for each ground station.
    list_args = []
    for ground_station in ground_stations:
        satellites_in_range = []
        for sid in range(len(satellites)):
            list_args.append((ground_station, satellites[sid], sid, t))


    pool = Pool(number_of_threads)
    ground_station_satellites_in_range_temporary = pool.map(calc_distance_gs_sat_worker, list_args)
    pool.close()
    pool.join()

    # Find the best satellite
    if association_criteria == "BASED_ON_DISTANCE_ONLY_GRAPH":
        return G_gs_sat_association_criteria_BasedOnDistance(G, ground_station_satellites_in_range_temporary, ground_stations, len(satellites))

    return -1

def G_gs_sat_association_criteria_BasedOnDistance(G, all_gs_satellites_in_range, actual_sat_number_to_counter, ground_stations, num_of_satellites):
    # The count of GSL links equals to the number of ground stations because each GS can only be associated with one satellite
    gsls = [0 for i in range(len(ground_stations))]
    ground_station_satellites_in_range = []

    for inrange_sat in all_gs_satellites_in_range:
        if len(inrange_sat[0]) != 0:
            ground_station_satellites_in_range.append(inrange_sat[0][0])

    for gid in range(len(ground_stations)):
        chosen_sid = -1
        best_distance_m = 1000000000000000
        for (distance_m, sid, gr_id) in ground_station_satellites_in_range:
            if gid == gr_id:
                if distance_m < best_distance_m:
                    chosen_sid = sid
                    best_distance_m = distance_m

        if chosen_sid != -1:
            G.add_edge(chosen_sid, num_of_satellites+gid, weight=1)
            gsls[gid] = chosen_sid
            print "best distance ",gid, chosen_sid, best_distance_m

    return {
            "Graph": G,
            "GSL_Connectivity": gsls
        }

def mininet_add_GSLs(connectivity_matrix, satellites, actual_sat_number_to_counter, ground_stations, t, number_of_threads, association_criteria):
    # find all satellites in range for each ground station.
    list_args = []
    for ground_station in ground_stations:
        satellites_in_range = []
        for sid in range(len(actual_sat_number_to_counter)):
            list_args.append((ground_station, satellites[str(actual_sat_number_to_counter[sid])], sid, t))


    pool = Pool(number_of_threads)
    ground_station_satellites_in_range_temporary = pool.map(calc_distance_gs_sat_worker, list_args)
    pool.close()
    pool.join()

    # Find the best satellite
    if association_criteria == "BASED_ON_DISTANCE_ONLY_MININET":
        return M_gs_sat_association_criteria_BasedOnDistance(connectivity_matrix, ground_station_satellites_in_range_temporary, ground_stations, len(satellites))

    return -1

def M_gs_sat_association_criteria_BasedOnDistance(connectivity_matrix, all_gs_satellites_in_range, ground_stations, num_of_satellites):
    ground_station_satellites_in_range = []

    for inrange_sat in all_gs_satellites_in_range:
        if len(inrange_sat[0]) != 0:
            ground_station_satellites_in_range.append(inrange_sat[0][0])

    for gid in range(len(ground_stations)):
        chosen_sid = -1
        best_distance_m = 1000000000000000
        for (distance_m, sid, gr_id) in ground_station_satellites_in_range:
            if gid == gr_id:
                if distance_m < best_distance_m:
                    chosen_sid = sid
                    best_distance_m = distance_m

        if chosen_sid != -1:
            connectivity_matrix[chosen_sid][num_of_satellites+gid] = 1
            connectivity_matrix[num_of_satellites+gid][chosen_sid] = 1
            # print "best distance ",gid, chosen_sid, best_distance_m

    return connectivity_matrix
