from skyfield.api import N, W, wgs84, load, EarthSatellite
import time

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

def graph_add_ISLs(G, satellites, current_planes, n_orbits, n_sats_per_orbit, isl_config):
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

    # if isl_config == "BASED_ON_DISTANCE_MAX_FOUR_ISL_PER_SAT":

    return G

def graph_add_GSLs(G, satellites, ground_stations, t, number_of_threads, association_criteria):
    # find all satellites in range for each ground station.
    list_args = []
    for ground_station in ground_stations:
        satellites_in_range = []
        for sid in range(len(satellites)):
            list_args.append((ground_stations, ground_station, satellites[sid], sid, t))


    pool = Pool(number_of_threads)
    ground_station_satellites_in_range_temporary = pool.map(calc_distance_gs_sat_worker, list_args)
    pool.close()
    pool.join()

    # Find the best satellite
    if association_criteria == "BASED_ON_DISTANCE_ONLY":
        return gs_sat_association_criteria_BasedOnDistance(G, ground_station_satellites_in_range_temporary, ground_stations)

    return -1

def gs_sat_association_criteria_BasedOnDistance(G, all_gs_satellites_in_range, ground_stations):
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
            G.add_edge(chosen_sid, len(satellites)+gid, weight=1)
            gsls[gid] = chosen_sid
            print "best distance ",gid, chosen_sid, best_distance_m

    return {
            "Graph": G,
            "GSL_Connectivity": gsls
        }
