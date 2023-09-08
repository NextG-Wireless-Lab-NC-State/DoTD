from skyfield.api import N, W, wgs84, load, EarthSatellite
import time
from multiprocessing import Process, Manager, Pool
import itertools
import math
import threading

import sys
sys.path.append("../")
from utils.utils import *
from mobility.read_gs import *

main_configurations = parse_config_file_yml(".","../controller/starlink_config.yml")

ts = load.timescale()
t = ts.utc(int(2023), int(3), int(13), int(13), int(2), int(25))
max_gsl_length_m = 1089686.4181956202 

path_of_recent_TLE = get_recent_TLEs_using_datetime("../utils/", "2023,03,13,13,2,25", "starlink")
tle_timestamp = path_of_recent_TLE.split("_")[2]
satellites = load.tle_file(path_of_recent_TLE)
satellites_by_name = {sat.name.split(" ")[0]: sat for sat in satellites}
satellites_by_index = {}

ground_stations = read_gs("ground_stations_experiments.txt")

orbital_data = get_orbital_planes_classifications(path_of_recent_TLE, "starlink", 72, 22, 53)
arranged_sats = arrange_satellites("../utils/", orbital_data, satellites_by_name, main_configurations, t, satellites_by_index, tle_timestamp)
satellites_by_index = arranged_sats["satellites by index"]

list_args = []
for ground_station in ground_stations:
    satellites_in_range = []
    for sid in range(len(satellites_by_index)):
        list_args.append((ground_station, satellites_by_name[str(satellites_by_index[sid])], sid, t, max_gsl_length_m))

number_of_threads = 12

for thread in number_of_threads
    ground_station_satellites_in_range_temporary = calc_distance_gs_sat_worker(list_args)

# pool = Pool(number_of_threads)
# ground_station_satellites_in_range_temporary = pool.map(calc_distance_gs_sat_worker, list_args)

# pool.close()
# pool.join()
print("map output = "+str(ground_station_satellites_in_range_temporary))
