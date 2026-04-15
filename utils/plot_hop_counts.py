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

# =================================================================================== #
# -------------------------------- MAIN FUNCTION ------------------------------------ #
# =================================================================================== #

import numpy as np

# Function to read the data from a file and load it into a NumPy array
def read_data_to_numpy_array(filename):
    with open(filename, 'r') as file:
        line = file.readline().strip()  # Read the line and remove extra whitespace
        # Convert the line to a list and then to a NumPy array
        data = np.array(eval(line))
    return data

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
    path_of_recent_TLE  = get_recent_TLEs_using_timestamp("./", time_timestamp, main_configurations["constellation"]["operator"])
    tle_timestamp       = path_of_recent_TLE.split("_")[2]

    # Load the satellites from the TLE file
    # satellites = load.tle_file("../controller/starlink_tles_to_use_v1")
    satellites = load.tle_file(path_of_recent_TLE)
    # Create dictionaries of satellites by name and index
    satellites_by_name = {sat.name.split(" ")[0]: sat for sat in satellites}
    satellites_by_index = {}

    # Read the ground stations from the file specified in the configurations
    ground_stations = read_gs(main_configurations["ground_stations"]["gs_file"])

    # Get the orbital data and arrange the satellites in the orbits
    # orbital_data  = get_orbital_planes_classifications("../controller/starlink_tles_to_use_v1", main_configurations["constellation"]["operator"], main_configurations["constellation"]["shell1"]["orbits"], main_configurations["constellation"]["shell1"]["sat_per_orbit"], main_configurations["constellation"]["shell1"]["inclination"])
    # orbital_data  = get_orbital_planes_classifications(path_of_recent_TLE, main_configurations["constellation"]["operator"], main_configurations["constellation"]["shell1"]["orbits"], main_configurations["constellation"]["shell1"]["sat_per_orbit"], main_configurations["constellation"]["shell1"]["inclination"])
    # arranged_sats = arrange_satellites("../output/", orbital_data, satellites_by_name, main_configurations, time_utc ,satellites_by_index, tle_timestamp)
    # satellites_by_index = arranged_sats["satellites by index"]
    # satellites_sorted_in_orbits = arranged_sats["sorted satellite in orbits"]

    # Get the total number of satellites and ground stations
    # num_of_satellites = len(orbital_data)
    # num_of_ground_stations = len(ground_stations)

    f_plus_grid  = read_data_to_numpy_array("../Farzad/GRID+/best_path_2024_01_19_17_0_1.0.txt")
    f_motif      = read_data_to_numpy_array("../Farzad/Motif/best_path_2024_01_19_17_0_2.0.txt")
    f_cross_grid = read_data_to_numpy_array("../Farzad/XGRID/best_path_2024_01_19_17_0_1.0 copy.txt") 
    f_next = read_data_to_numpy_array("../Farzad/DoTD/best_path_2024_01_19_17_0_1.0.txt")

    sats_next = []
    for sat in f_next:
        sat_x = sat / 9
        sat_y = sat % 8
        sats_next.append((sat_x, sat_y))

    sats_plus = []
    for sat in f_plus_grid:
        sat_x = sat / 9
        sat_y = sat % 8
        sats_plus.append((sat_x, sat_y))

    sats_x = []
    for sat in f_cross_grid:
        sat_x = sat / 9
        sat_y = sat % 8
        sats_x.append((sat_x, sat_y))

    sats_motif = []
    for sat in f_motif:
        sat_x = sat / 9
        sat_y = sat % 8
        sats_motif.append((sat_x, sat_y))


    # Extract x and y coordinates from each set
    sats_plus_x, sats_plus_y = zip(*sats_plus)
    sats_x_x, sats_x_y = zip(*sats_x)
    sats_motif_x, sats_motif_y = zip(*sats_motif)
    sats_next_x, sats_next_y = zip(*sats_next)


    # Plotting
    plt.figure(figsize=(8, 6))

    # Plot sats_plus
    # plt.plot(sats_plus_y, color='r', marker='o', label='+Grid')

    # plt.plot(sats_x_y, color='b', marker='x', label='XGrid')

    plt.plot(sats_next_x, sats_next_y, color='g', marker='x', label='sats_dotd')
    # plt.plot(sats_motif_y, color='g', marker='.', label='Motif')

    plt.legend()
    # Plot sats_x
    # plt.plot(sats_x_x, sats_x_y, color='g', marker='x', label='sats_x')

    # Plot sats_next

    plt.show()




if __name__ == '__main__':
    main()