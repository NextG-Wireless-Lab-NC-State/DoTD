import os
import numpy as np
import math

import sys
sys.path.append("../")
from mobility.mobility_utils import *

channelFreq_isls                        = 37.0;             # in GHz
channelFreq_sat_to_ground               = 12.7;             # in GHz
channelFreq_ground_to_sat               = 14.5;             # in GH
channnel_bandwidth_downlink             = 50;               #MHz
channnel_bandwidth_uplink               = 50;               #MHz
polarization_loss                       = 3;                #dBi
misalignment_attenuation_losses         = 0.5;              #dB
###
# file:///Users/mk0052/Downloads/FCC-05-63A1.pdf
# 10 dBW/4KHz, given channel bandwidth is 50 MHz
# Max EIRP = 50.9 dBw or 80.9 dBm
###
satellite_eirp                          = 80.9;

ground_station_tx_power                 = 36.08526;         #dBm -- https://apps.fcc.gov/els/GetAtt.html?id=259301
ground_station_receive_attenna_gain     = 33.2;             #dBi -- https://apps.fcc.gov/els/GetAtt.html?id=259301
ground_station_transmit_attenna_gain    = 34.6;             #dBi -- https://apps.fcc.gov/els/GetAtt.html?id=259301

def calc_gsl_snr(satellite, ground_station, t):
    gsl_distance = distance_between_ground_station_satellite(ground_station, satellite, t);

    fspl = 20 * math.log10(gsl_distance/1000) + 20 * math.log10(channelFreq_sat_to_ground) + 92.45;

    rss_dBm = satellite_eirp - 2 + ground_station_receive_attenna_gain - fspl - polarization_loss - misalignment_attenuation_losses - 1.0;
    rss_watt = pow(10,((rss_dBm - 30)/10));

    noise_watt = 200 * 1.38064852 * pow(10, -23) * channnel_bandwidth_downlink*pow(10, 6);        #ktB

    snr = rss_watt/noise_watt;

    return snr

def calc_gsl_snr_given_distance(gsl_distance):
    fspl = 20 * math.log10(gsl_distance/1000) + 20 * math.log10(channelFreq_sat_to_ground) + 92.45;

    rss_dBm = satellite_eirp - 2 + ground_station_receive_attenna_gain - fspl - polarization_loss - misalignment_attenuation_losses - 1.0;
    rss_watt = pow(10,((rss_dBm - 30)/10));

    noise_watt = 200 * 1.38064852 * pow(10, -23) * channnel_bandwidth_downlink*pow(10, 6);        #ktB

    snr = rss_watt/noise_watt;

    return snr

def calc_isl_throughput_given_distance(isl_distance):
    return 20
