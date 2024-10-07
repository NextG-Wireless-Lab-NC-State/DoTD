# =================================================================================== #
# ------------------------------- IMPORT PACKAGES ----------------------------------- #
# =================================================================================== #

from tqdm import tqdm
from utils import *
import time
import sys
sys.path.append("../")
from mobility.read_live_tles import *
from mobility.mobility_utils import *
from mobility.read_gs import *
from routing.routing_utils import *
from routing.constellation_routing import *
from mobility.DoTD import DoTD_History

# =================================================================================== #
# -------------------------------- MAIN FUNCTION ------------------------------------ #
# =================================================================================== #

def main():

    # Parse the main configurations from the YAML file
    main_configurations = parse_config_file_yml(".","../controller/starlink_config.yml")

    # Load the timescale and initialize variables
    ts = load.timescale()
    inc = 0
    indx = 1
    time_resolution_in_seconds = main_configurations["simulation"]["step"]

    # Split the start time from the configurations into individual components
    y,mon,d,h,min,s = main_configurations["simulation"]["start_time"].split(",")

    # Convert the start time to UTC and Unix timestamp
    time_utc = ts.utc(int(y), int(mon), int(d), int(h), int(min), float(s))
    time_timestamp = convert_time_utc_to_unix(time_utc)
    print((y,mon,d,h,min,s))

    # Get the path of the most recent TLE file based on the timestamp
    # path_of_recent_TLE  = get_recent_TLEs_using_timestamp("/home/farzad/repos/SimLEO_MConstellations/utils/", time_timestamp, main_configurations["constellation"]["operator"])
    tle_timestamp = str(int(time_timestamp))
    print(tle_timestamp)
    # tle_timestamp       = path_of_recent_TLE.split("_")[-1]

    # Load the satellites from the TLE file
    satellites = load.tle_file("/home/farzad/repos/SimLEO_MConstellations/tles/gp.txt")
    # satellites = load.tle_file(path_of_recent_TLE)
    # Create dictionaries of satellites by name and index
    satellites_by_name = {sat.name.split(" ")[0]: sat for sat in satellites}
    satellites_by_index = {}

    # Read the ground stations from the file specified in the configurations
    ground_stations = read_gs(main_configurations["ground_stations"]["gs_file"])

    # Get the orbital data and arrange the satellites in the orbits
    orbital_data  = get_orbital_planes_classifications("/home/farzad/repos/SimLEO_MConstellations/tles/gp.txt", main_configurations["constellation"]["operator"], main_configurations["constellation"]["shell1"]["orbits"], main_configurations["constellation"]["shell1"]["sat_per_orbit"], main_configurations["constellation"]["shell1"]["inclination"])
    # orbital_data  = get_orbital_planes_classifications(path_of_recent_TLE, main_configurations["constellation"]["operator"], main_configurations["constellation"]["shell1"]["orbits"], main_configurations["constellation"]["shell1"]["sat_per_orbit"], main_configurations["constellation"]["shell1"]["inclination"])
    
    # same_orbit = np.zeros((len(satellites),len(satellites)))
    # for i, sat1 in enumerate(satellites):
    #     for j, sat2 in enumerate(satellites):
    #         # same_orbit[i,j] = 
    #         ra, dec, distance = sat1.at(time_utc).radec()
    #         # same_orbit[i] = sat1.

    # for m = 1:length(sat)
    # sat1 = orbitalElements(sat(m)); RAAN = zeros(1,length(sat));
    # SameOrbit = zeros(1,length(sat));
    # for n = 1:length(sat)
    #     sat2 = orbitalElements(sat(n));
    #     RAAN(n) = sat1.RightAscensionOfAscendingNode - sat2.RightAscensionOfAscendingNode;
    #     isSameOrbit = compareOrbits(sat1, sat2, tolerance, toleranceRAAN);
    #     SameOrbit(n) = isSameOrbit;
    # end
    
    
    arranged_sats = arrange_satellites("/home/farzad/repos/SimLEO_MConstellations/output/", orbital_data, satellites_by_name, main_configurations, time_utc ,satellites_by_index, tle_timestamp)
    satellites_by_index = arranged_sats["satellites by index"]
    satellites_sorted_in_orbits = arranged_sats["sorted satellite in orbits"]

    # Get the total number of satellites and ground stations
    num_of_satellites = len(orbital_data)
    num_of_ground_stations = len(ground_stations)

    # Print debug information if enabled in the configurations
    if main_configurations["simulation"]["debug"] == 1:
        print((".......... total number of satellites = ", num_of_satellites))
        print((".......... total number of ground_stations = ", num_of_ground_stations))

    # Initialize the optimal routes per timestep and time history
    optimal_routes_per_timestep = []
    time_hist = np.arange(0, main_configurations["simulation"]["length"], time_resolution_in_seconds)
    # M, e = motif_find_m_se_e(satellites_sorted_in_orbits, satellites_by_name, satellites_by_index, time_utc)
    M = None
    e = None
    # Loop over the time history, update the topology and save it in a file
    history_dotd = DoTD_History(num_of_satellites, len(time_hist))
    for inc in tqdm(time_hist, total=len(time_hist)):
        
        # Update the time
        indx += 1
        sec = float(s)+inc
        if (sec)%60 == 0:
            min=int(min)+1
            s = 0.0
            inc = 0
            sec = 0.0

        if (int(min))%60 == 0 and int(min) != 0:
            h=int(h)+1
            s = 0.0
            inc = 0
            sec = 0.0
            min = 0

        # Convert the updated time to UTC and Unix timestamp
        time_utc_inc = ts.utc(int(y), int(mon), int(d), int(h), int(min), sec)
        time_timestamp = convert_time_utc_to_unix(time_utc_inc)

        # Get the path of the most recent TLE file based on the updated timestamp
        # new_file = get_recent_TLEs_using_timestamp("./", time_timestamp, main_configurations["constellation"]["operator"])

        # # If the TLE file has changed, reload the satellites
        # if  new_file != path_of_recent_TLE:
        #     path_of_recent_TLE = new_file
        #     reloaded_vars = reload_tles(path_of_recent_TLE, main_configurations, time_utc, ground_stations)
        #     satellites_sorted_in_orbits = reloaded_vars["satellites_sorted_in_orbits"]
        #     satellites_by_name = reloaded_vars["satellites_by_name"]
        #     satellites_by_index = reloaded_vars["satellites_by_index"]
        #     num_of_satellites = reloaded_vars["num_of_satellites"]

        # Update the size of the connectivity matrix
        conn_mat_size = num_of_satellites + num_of_ground_stations

        # Initialize the connectivity matrix
        connectivity_matrix = [[0 for _ in range(conn_mat_size)] for r in range(conn_mat_size)]

        # Add ISLs and GSLs to the connectivity matrix (FIX) <-----------------
        if main_configurations["constellation"]["operator"] == "oneweb":
            connectivity_matrix = mininet_add_ISLs(connectivity_matrix, satellites_sorted_in_orbits, satellites_by_name, satellites_by_index, "SAME_ORBIT_AND_GRID_ACROSS_ORBITS_ONEWEB", time_utc_inc)
        else:
            connectivity_matrix = mininet_add_ISLs(connectivity_matrix, satellites_sorted_in_orbits, satellites_by_name, satellites_by_index, main_configurations["constellation"]["topology"]["association_criteria_ISL"], time_utc_inc, M, e, dotd=history_dotd)
        connectivity_matrix = mininet_add_GSLs_parallel(connectivity_matrix, satellites_by_name, satellites_by_index, ground_stations, 2, main_configurations["constellation"]["topology"]["association_criteria_GSL"], time_utc_inc, main_configurations)

        # Calculate the link characteristics for GSLs and ISLs
        links_charateristics = calculate_link_charateristics_for_gsls_isls(connectivity_matrix, satellites_by_index, satellites_by_name, ground_stations, time_utc_inc)

        # Save the topology
        save_topology(connectivity_matrix, links_charateristics, main_configurations, str(y)+"_"+str(mon)+"_"+str(d)+"_"+str(h)+"_"+str(min)+"_"+str(sec))

        # Pre-compute the routing tables
        all_possible_routes = initial_routing_v2(satellites_by_index, ground_stations, connectivity_matrix, links_charateristics["latency_matrix"])

        # Get the source and destination nodes
        source_node         = num_of_satellites + int(''.join(filter(str.isdigit, main_configurations["application"]["source"])))
        destination_node    = num_of_satellites + int(''.join(filter(str.isdigit, main_configurations["application"]["destination"])))

        # Get the optimal route and add it to the list of optimal routes per timestep
        optimal_route       = get_optimal_route(satellites=satellites_by_index, ground_stations=ground_stations, connectivity_matrix=connectivity_matrix, source=source_node, destination=destination_node)
        optimal_routes_per_timestep.append(optimal_route)

        # Save the routes
        save_routes(all_possible_routes, main_configurations, str(y)+"_"+str(mon)+"_"+str(d)+"_"+str(h)+"_"+str(min)+"_"+str(float(s)+inc))

    # Save the optimal path
    save_optimal_path(optimal_routes_per_timestep, main_configurations, str(y)+"_"+str(mon)+"_"+str(d)+"_"+str(h)+"_"+str(min)+"_"+str(float(s)+inc))



if __name__ == '__main__':
    main()