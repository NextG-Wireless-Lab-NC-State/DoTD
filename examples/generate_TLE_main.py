''''

SpaceNet: Generate Fake Two-Line Element Sets (TLE)

AUTHOR:         Bruce L. Barbour, 2023
                Virginia Tech


This Python script supplies a function to generate Two-Line Element Sets of
virtual (fake) satellites and writes them into a file.
'''

# =================================================================================== #
# ------------------------------- IMPORT PACKAGES ----------------------------------- #
# =================================================================================== #

import os
import time
import numpy as np
import generate_fake_TLE as gft

# =================================================================================== #
# -------------------------------- MAIN FUNCTION ------------------------------------ #
# =================================================================================== #

def basic_generate_fake_TLE(
                                epoch       : np.ndarray,
                                oe          : np.ndarray,
                                ta_range    : np.ndarray,
                                inc_range   : np.ndarray
                           )   -> list[str]:
    """
    Generates virtual satellite TLEs using the user-input epoch, orbital elements (oe), and
    range of values of True Anomaly (TA) and Inclincation. This is a basic function that
    considers only variation in TA and Inclination. In addition, spacecraft collisions are 
    NOT considered. 

    **HAVE NOT ADDED IN INCLINATION RANGE YET. - BRUCE

    Args:
        epoch (np.ndarray):     Last two digits of epoch year and day of year (with fraction)  -> e.g., [97, 210.21344211]
        oe (np.ndarray):        Keplerian orbital elements (a-km, e, i-deg, aop-deg, raan-deg, ta-deg)
        ta_range (np.ndarray):  Range of True Anomaly values to generate virtual satellite TLEs, in deg
        inc_range (np.ndarray): Range of Inclincation values to generate virtual satellite TLEs, in deg
    
    Returns:
        list [str]:             List of TLE formats written as String instances
    """

    # Initialize OE sweep array
    oe_sweep    = oe

    # Check if TA range is provided, then add in TA numbers
    if ta_range is not None and len(ta_range) > 1:
        oe_sweep = np.resize(oe_sweep, (len(ta_range), 6))
        for indx, oe_line in enumerate(oe_sweep):
            oe_line[5] = ta_range[indx]
    elif ta_range is not None and len(ta_range) == 1:
        oe_sweep[5] = ta_range[0]

    # Initialize TLE list
    TLE_output  = [""] * len(oe_sweep)

    # Perform sweep of TLEs
    for indx, oe_line in enumerate(oe_sweep):

        # Generate fake TLE
        TLE_output[indx] = gft.generate_virtual_TLE(epoch=epoch, oe=oe_line, iter_num=indx)

    
    return TLE_output



# =================================================================================== #
# ----------------------------------- RUN SIM --------------------------------------- #
# =================================================================================== #

if __name__ == "__main__":


    # File name
    filename    = "TLE_fake_" + str(int(time.time()))

    # Epoch Year / Fractional Day
    epoch       = [23, 256.32350922421132]

    # Orbital Elements (a-km, e, i-deg, w-deg, raan-deg, TA-deg)
    oe          = [6800, 0.00001, 0.000000, 0.000000, 120.000000, 0.0000000]

    # Range of TA
    ta_range    = np.array(range(0, 360, 30))

    # Range of Inc
    inc_range   = None


    # -------------------------------------------------------------------------------
    # Generate TLE sweep

    TLE_sweep = basic_generate_fake_TLE(epoch=epoch, oe=oe, ta_range=ta_range, inc_range=inc_range)

    # -------------------------------------------------------------------------------

    # -------------------------------------------------------------------------------
    # Write to a file

    with open(filename, 'a') as file:
        for TLE in TLE_sweep:
            file.write(TLE + '\n')

    # -------------------------------------------------------------------------------
    


