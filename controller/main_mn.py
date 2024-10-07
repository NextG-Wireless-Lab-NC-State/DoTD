
# =================================================================================== #
# ------------------------------- IMPORT PACKAGES ----------------------------------- #
# =================================================================================== #

from mininet.net import Mininet
from mininet.link import TCLink
from mininet.link import *
from mininet.log import setLogLevel
from mininet.node import OVSController
import time
import os
import time
import sys
sys.path.append("../")
from mobility.read_live_tles import *
from mobility.mobility_utils import *
from mobility.read_gs import *
from mininet_infra.create_mininet_topology import *
from routing.routing_utils import *
from routing.constellation_routing import *
from utils.utils import *

import topology.visualize_topology as vt

# =================================================================================== #
# -------------------------------- MAIN FUNCTION ------------------------------------ #
# =================================================================================== #

def main():
    
    # ===========================================================================================================
    # ========================================== CONFIGURATION ==================================================
    # ===========================================================================================================

    old_connectivity_matrix = None
    # Constants and timescale
    N = 3   # This is a constant value -- it's unclear what it represents
    ts = load.timescale()  # Load a timescale object from the Skyfield API.

    # Configuration and TLE data
    main_configurations = parse_config_file_yml(".","starlink_config.yml")  # Parse the main configurations from the YAML file.
    # path_of_recent_TLE = get_recent_TLEs_using_datetime("../utils/", main_configurations["simulation"]["start_time"], main_configurations["constellation"]["operator"])  # Get the path of the most recent TLE file.
    # path_of_recent_TLE = "/home/farzad/repos/SimLEO_MConstellations/utils/fake_TLE_generation/TLE_fake_1707853243"
    # print("Recent TLE path: ", path_of_recent_TLE)  # Print the path of the recent TLE file.

    # Satellite data
    # satellites = load.tle_file("/home/farzad/repos/SimLEO_MConstellations/controller/starlink_tles_to_use_v1")  # Load the satellites from the TLE file.
    satellites = load.tle_file("/home/farzad/repos/SimLEO_MConstellations/tles/gp.txt")  # Load the satellites from the TLE file.
    satellites_by_name = {sat.name.split(" ")[0]: sat for sat in satellites}  # Create a dictionary of satellites by name.
    satellites_by_index = {}  # Initialize an empty dictionary for satellites by index.

    # Orbital data
    orbital_data = get_orbital_planes_classifications("/home/farzad/repos/SimLEO_MConstellations/tles/gp.txt", main_configurations["constellation"]["operator"], main_configurations["constellation"]["shell1"]["orbits"], main_configurations["constellation"]["shell1"]["sat_per_orbit"], main_configurations["constellation"]["shell1"]["inclination"])  # Get the orbital data and classify the orbital planes.
    # orbital_data = get_orbital_planes_classifications("/home/farzad/repos/SimLEO_MConstellations/controller/starlink_tles_to_use_v1", main_configurations["constellation"]["operator"], main_configurations["constellation"]["shell1"]["orbits"], main_configurations["constellation"]["shell1"]["sat_per_orbit"], main_configurations["constellation"]["shell1"]["inclination"])  # Get the orbital data and classify the orbital planes.

    # Arranging satellites
    arranged_sats = arrange_satellites("/home/farzad/repos/SimLEO_MConstellations/output/", orbital_data, satellites_by_name, main_configurations, main_configurations["simulation"]["start_time"] ,satellites_by_index, str(int(time_timestamp)))  # Arrange the satellites in the orbits.
    satellites_by_index = arranged_sats["satellites by index"]  # Update the dictionary of satellites by index.

    # Ground station data
    ground_stations = read_gs(main_configurations["ground_stations"]["gs_file"])  # Read the ground stations from the file specified in the configurations.

    # Counting entities
    num_of_satellites = len(orbital_data)  # Get the total number of satellites.
    num_of_ground_stations = len(ground_stations)  # Get the total number of ground stations.

    # Miscellaneous
    increments = 0  # Initialize a variable for increments.
    TopologyRoutes = {}  # Initialize an empty dictionary for topology routes.

    # Sanity checks
    print("Total number of satellites = ", num_of_satellites)  # print the total number of satellites,
    print("Total number of ground_stations = ", num_of_ground_stations)  # and the total number of ground stations.
    print("------------------------------------------------------------------")  # print a separator line.

    # Simulation time
    sim_timeCount = main_configurations["simulation"]["length"]  # Get the simulation length from the configurations.


    # ===========================================================================================================
    # ====================================== START OF WHILE LOOP ================================================
    # ===========================================================================================================
    

    # Begin execution of the simulation
    while sim_timeCount >= 1:

        # Split the start time from the configuration into year, month, day, hour, minute, and second.
        year,month,day,hour,minute,second = main_configurations["simulation"]["start_time"].split(",")[0], main_configurations["simulation"]["start_time"].split(",")[1], main_configurations["simulation"]["start_time"].split(",")[2], main_configurations["simulation"]["start_time"].split(",")[3], main_configurations["simulation"]["start_time"].split(",")[4], main_configurations["simulation"]["start_time"].split(",")[5]

        # Convert the incremented time to UTC.
        # The incremented time is added to the seconds component of the start time.
        # The ts.utc function converts the year, month, day, hour, minute, and second into a UTC time.
        time_utc_inc    = ts.utc(int(year), int(month), int(day), int(hour), int(minute), float(second)+increments)
        
        # Convert the UTC time to a Unix timestamp.
        time_timestamp  = convert_time_utc_to_unix(time_utc_inc)
        
        # If the most recent TLE file for the current timestamp is different from the previously loaded TLE file,
        # if get_recent_TLEs_using_timestamp("../utils/", time_timestamp, main_configurations["constellation"]["operator"]) != path_of_recent_TLE:
            
        #     # Update the path of the most recent TLE file.
        #     path_of_recent_TLE              = get_recent_TLEs_using_timestamp("../utils/", time_timestamp, main_configurations["constellation"]["operator"])
            
        #     # Reload the TLE data.
        #     reloaded_vars                   = reload_tles(path_of_recent_TLE)
            
        #     # Update the satellite data.
        #     satellites_by_name              = reloaded_vars["satellites_by_name"]
        #     satellites_by_index             = reloaded_vars["satellites_by_index"]
        #     num_of_satellites               = reloaded_vars["num_of_satellites"]

	    # Calculate the size of the connectivity matrix.
        conn_mat_size           = num_of_satellites + num_of_ground_stations

        # Parse the connectivity matrix and characteristics.
        satnat_topology_change  = parse_connectivity_matrix_n_charateristics(time_utc_inc, conn_mat_size, main_configurations["data_n_results"]["connectivity_matrix"])

        # If there is an error in parsing the connectivity matrix and characteristics,
        if satnat_topology_change == -1:

            # Print an error message and exit the program.
            print ("[Error] Check the parse_connectivity_matrix_n_charateristics function")
            exit()


        # ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
        # This block of code only executes for the first run of the simulator.
        # ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
        if increments == main_configurations["simulation"]["step"]-1 or old_connectivity_matrix is None:
           
            # Get the ground station-satellite pairs from the connectivity matrix.
            gs_statellite_pair  = get_gs_sat_pairs(satnat_topology_change["connectivity_matrix"], num_of_satellites)
            
            # Generate IP addresses for the constellation based on the IP range specified in the configuration.
            available_ips       = generate_ips_for_constellation(main_configurations["constellation"]["routing"]["ip_range"])

            # Parse the topology routes. This is disabled for dynamic routing.
            TopologyRoutes      = parse_topology_routes(main_configurations["data_n_results"]["routing"], num_of_satellites, time_utc_inc)

            # If there is an error in parsing the topology routes, print an error message and exit the program.
            if TopologyRoutes == -1:
                print ("[Error] Check the parse_topology_routes function")
                exit()

            # Create a new file to write the links.
            absolute_path   = "/home/farzad/repos/SimLEO_MConstellations/output/general/starlink/"
            file            = open(absolute_path+"links.txt", 'w')
            
            # ************************************************************
            # **************** START OF MININET INTERFACE ****************
            # ************************************************************

            # Create the satellite network using the Mininet interface.
            topology                = sat_network(N=N)
            topg                    = topology.create_sat_network(satellites=satellites_by_index, ground_stations=ground_stations, connectivity_matrix=satnat_topology_change["connectivity_matrix"], link_throughput=satnat_topology_change["links_capacity"], link_latency=satnat_topology_change["links_latency"], physical_gs_index=[], physical_sats_index=[], border_gateway=main_configurations["constellation"]["routing"]["border_gateway"])
            net                     = Mininet(topo = topology, link=TCLink, autoSetMacs = True, controller=OVSController)
            net.start()
            list_of_Intf_IPs        = topology.initial_ipv4_assignment_for_interfaces_optimised(main_configurations["data_n_results"]["simulation_results"], net, available_ips, main_configurations["constellation"]["routing"]["border_gateway"])
            
            # Visualize topology at current time step
            # vt.visualize(arranged_sats, topg["isl_gls_links"], time_utc_inc)

            # Initialize a dictionary to store the links.
            links_hash              = {}

            # Write the ISL-GSL links to the file and add them to the dictionary.
            for link in topg["isl_gls_links"]:
                file.write(str(link)+"\n")
                endpoint1, endpoint2         = link.split(":")
                endpoints                    = str(endpoint1.split("-")[0])+"_"+str(endpoint2.split("-")[0])
                links_hash[str(endpoints)]   = []
                links_hash[str(endpoints)].append(link)
            file.close()
            
            
            # Prepare the routing configuration commands. This function generates the necessary commands to configure the routing in the network.
            prepare_routing_config_commands(topology, main_configurations["data_n_results"]["simulation_results"], TopologyRoutes["All_PreConfigured_routes"], links_hash, list_of_Intf_IPs, satellites_by_index, 20)

            # Configure the routing for the ground stations. This function sets up the routing tables for the ground stations in the network.
            gs_routing(main_configurations["data_n_results"]["simulation_results"], gs_statellite_pair, links_hash, num_of_satellites, satellites_by_index, list_of_Intf_IPs, TopologyRoutes["Routes_per_satellites"], main_configurations, main_configurations["constellation"]["routing"]["border_gateway"])

            # Start the routing configuration. This function applies the routing configuration to the network.
            # Note: This function is currently causing issues with bash scripts and needs further investigation.
            topology.startRoutingConfigV2(main_configurations["data_n_results"]["simulation_results"], net, satellites_by_index)

            # Run the network performance utility. This function runs a network performance application to measure the performance of the network.
            net = run_application(main_configurations["data_n_results"]["simulation_results"], net, main_configurations, list_of_Intf_IPs, increments)


        # ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
        # For every other run outside of the first. Keeps Mininet interface running from first run.
        # ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
        else:

            # Track changes in the network topology and update the Mininet network object accordingly.
            # Note: This section needs further investigation.
            # Check for changes in the network topology.
            topology_changes = check_changes_in_topology(old_connectivity_matrix, satnat_topology_change["connectivity_matrix"])
            
            # Check for changes in the latency of the links.
            latency_changes = check_changes_in_link_charateristics(old_links_latency, satnat_topology_change["links_latency"])
            
            # Check for changes in the capacity of the links.
            capacity_changes = check_changes_in_link_charateristics(old_links_capacity, satnat_topology_change["links_capacity"])
            
            # Merge the changes in link characteristics.
            links_charateristics_changes = merge_link_link_charateristics(latency_changes, capacity_changes)

            # Apply changes to the Mininet network object if there are any changes in the network topology.
            if len(topology_changes) > 0 and len(topology_changes) < 100:

                # Update the routing based on the changes in the network topology.
                lightweight_routing(main_configurations["data_n_results"]["simulation_results"], topology_changes, links_hash, num_of_satellites, satellites_by_index, list_of_Intf_IPs, TopologyRoutes["Routes_per_satellites"], time_utc_inc, main_configurations["constellation"]["routing"]["border_gateway"])
                
                # ************************************************************
                # ***************** MODS TO MININET INTERFACE ****************
                # ************************************************************

                # Apply the changes in the network topology to the ***Mininet network object.
                net = apply_topology_updates_to_mininet(main_configurations["data_n_results"]["simulation_results"], net, topology_changes, num_of_satellites, time_utc_inc)
                
                # Apply the changes in link characteristics to the ***Mininet network object.
                net = apply_link_updates_to_mininet(net, links_charateristics_changes[0], links_charateristics_changes[1], num_of_satellites, time_utc_inc)


        # ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
        # ||||||||||||||||||||||||||||| PROCEED TO REST OF WHILE LOOP ||||||||||||||||||||||||||||||||||
        # ||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||


        # Update the old connectivity matrix, links latency, and links capacity for the next iteration.
        old_connectivity_matrix = satnat_topology_change["connectivity_matrix"][:]
        old_links_latency = satnat_topology_change["links_latency"][:]
        old_links_capacity = satnat_topology_change["links_capacity"][:]

        # Decrement the simulation time count.
        sim_timeCount -= 1
        # Increment the simulation time by the step size specified in the configuration.
        increments += main_configurations["simulation"]["step"]

    
    # ===========================================================================================================
    # ======================================= END OF WHILE LOOP =================================================
    # ===========================================================================================================




setLogLevel('info')    # 'info' is normal; 'debug' is for when there are problems
if __name__ == "__main__":
    main()
