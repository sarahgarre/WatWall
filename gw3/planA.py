#!/usr/bin/env python2
# -*- coding: utf-8 -*-

# Packages of Christophe

from datetime import datetime
import time
import json
import math
import os, sys
import socket
import traceback
import urllib2 as urllib

user = "GW3"
test = True
# True to run the code locally
# False to implement the code on the server

# 1) Ensure to run in the user home directory
# !!! MUST NOT BE CHANGED !!!

if test:
    host = "greenwall.gembloux.uliege.be"
else:
    host = "localhost"
    # Ensure to run in the user home directory
    DIR_BASE = os.path.expanduser("~")
    if not os.path.samefile(os.getcwd(), DIR_BASE):
        os.chdir(DIR_BASE)
    print(os.getcwd())

    # 2)Ensure to be the only instance to run
    # !!! MUST NOT BE CHANGED !!!
    # Explanation: if another program is running, it gets killed and replaced by this one

    pid = str(os.getpid())
    _lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)

    try:
        _lock_socket.bind('\0' + user)
        print('Socket ' + user + ' now locked for process #' + pid)
        # Make the current pid available to be able to kill the process...
        open("pid.txt", 'w').write(pid)
    except socket.error:
        current = open("pid.txt", 'r').read()
        print(user + ' lock exists for process #' + current + " : may be you should ./clean.sh !")
        sys.exit()


# 3) Date determination
# !!! MUST NOT BE CHANGED !!!
# Explanation: EPOCH time is the number of seconds since 1/1/1970
def get_timestamp():
    return int(time.time())

# Transform an EPOCH time in a lisible date (for Grafana)
def formatDate(epoch):
    dt = datetime.fromtimestamp(epoch)
    return dt.isoformat()

# Transform an EPOCH time in a lisible date (for Grafana)
def formatDateGMT(epoch):
    dt = datetime.fromtimestamp(epoch - (2 * 60 * 60))  # We are in summer and in Belgium !
    return dt.isoformat()

delimiters = ' \t\n\r\"\''

# 4) Getting the list of all available sensors
# !!! MUST NOT BE CHANGED !!!

dataFile = None
try:  # urlopen not usable with "with"
    url = "http://" + host + "/api/grafana/search"
    dataFile = urllib.urlopen(url, json.dumps(""), 20)
    result = json.load(dataFile)
    for index in result:
        print(index)
except:
    print(u"URL=" + (url if url else "") + \
          u", Message=" + traceback.format_exc())
if dataFile:
    dataFile.close()

# 5) Irrigation scheme: collecting sensor readings, taking a decision to irrigate or not
# and sending the instructions to the valves

# !!! THIS IS WHERE WE MAKE CHANGES !!!
"""
Objective: Your program must create a data file with one column with the Linux EPOCH time
and your valve state (0=closed, 1=opened)
"""

while (True):

    # __________________________________________________________________
    # a. reading all values of the last 5 minutes (5 minutes of 60 seconds)

    """
    sensors' names:
        - HUM7 : first humidity sensor [V]
        - HUM8 : second humidity sensor [V]
        - HUM9 : third humidity sensor [V]
        - SDI11 : humidity sensor temperature [°C]
    """

    dataFile = None
    try:  # urlopen not usable with "with"
        url = "http://" + host + "/api/grafana/query"
        now = get_timestamp()
        gr = {'range': {'from': formatDateGMT(now - (1 * 5 * 60)), 'to': formatDateGMT(now)}, \
              'targets': [{'target': 'HUM7'}, {'target': 'HUM8'}, {'target': 'HUM9'}, {'target': 'SDI11'}]}
        data = json.dumps(gr)
        print(data)
        dataFile = urllib.urlopen(url, data, 20)
        result = json.load(dataFile)
        if result:
            print(result)
            for target in result:
                # print target
                index = target.get('target')
                for datapoint in target.get('datapoints'):
                    value = datapoint[0]
                    stamp = datapoint[1] / 1000
                    print(index + ": " + formatDate(stamp) + " = " + str(value))

    except:
        print(u"URL=" + (url if url else "") + \
              u", Message=" + traceback.format_exc())
    if dataFile:
        dataFile.close()

    # ________________________________________________________________________
    # b. Choose to use Plan A or not

    # ---------------------------------------------------------------------------
    # 1. Parameters

    # Acceptable standard deviation
    SD_threshold = 0.03         # Humidity sensor uncertainty[-]

    # Outliers
    outlier_max = 0.9  # Maximal water content that can be encountered [cm3/cm3]
    outlier_min = 0.3  # Minimal water content that can be encountered [cm3/cm3]

    # --------------------------------------------------------------------------
    # 2. Calculate indicators

    # ------------------------------
    # NaN values

    # Build lists
    HUM7 = []
    HUM8 = []
    HUM9 = []
    length_result = len(result[0].get('datapoints'))
    for i in range(0, length_result):
        HUM7.append(result[0].get('datapoints')[i][0])
        HUM8.append(result[1].get('datapoints')[i][0])
        HUM9.append(result[2].get('datapoints')[i][0])
    print 'HUM7 [V]', HUM7
    print 'HUM8 [V]', HUM8
    print 'HUM9 [V]', HUM9

    # Find NaN values
    HUM7_missing = []
    HUM8_missing = []
    HUM9_missing = []
    for i in range(0, length_result):
        HUM7_missing.append(math.isnan(HUM7[i]))
        HUM8_missing.append(math.isnan(HUM8[i]))
        HUM9_missing.append(math.isnan(HUM9[i]))
    # ------------------------------
    # Calculate Standard deviation of the signal

    # average signal [V]
    V_mean = []  # Initialization of the list containing mean voltage
    for i in range(3):
        length_result = len(result[i].get('datapoints'))
        V_sum = 0
        for j in range(0, length_result):
            V_sum += result[i].get('datapoints')[j][0]
        V_mean.append(V_sum / length_result)
    print 'V_mean [V]:', V_mean

    # standard deviation of the signal
    V_SD = []
    for i in range(3):
        length_result = len(result[i].get('datapoints'))
        V_var = 0  # Variance initialization
        for j in range(0, length_result):
            V_var += (result[i].get('datapoints')[j][0] - V_mean[i]) ** 2 / length_result
        V_SD.append(math.sqrt(V_var) / V_mean[i])
    print 'V_var [V]:', V_var
    print 'V_SD [-]:', V_SD

    # ___________________________________________________________________________
    # c. Convert analog signal [V] into digital signal [cm3/cm3]
    """
    1. With the calibration equation provided by the manufacturer
    Equation:   VWC = (-3.14E-07 * mV^2) + (1.16E-03 * mV) – 6.12E-01
    From:       LICOR, 8100_TechTip_EC-5_Probe_Connection_TTP24.pdf
    
    # Computation
    for i in range(3):  # loop on humidity sensors
        length_result = len(result[i].get('datapoints'))
        for j in range(0, length_result):   # loop on values
            mV = result[i].get('datapoints')[j][0] /1000            # divided by 1000 to convert to mV
            result[i].get('datapoints')[j][0] = (-3.14E-07 * mV**2) + (1.16E-03 * mV) - 6.12E-01
            print result[i].get('datapoints')[j][0]
    """

    """
        1. With the calibration equation of Cedric Bernard
        Equation:   VWC = (0.3524 * V - 0.1554)/(V - 0.3747)
        From: TFE of Cedric Bernard      
    """

    # Computation
    for i in range(3):  # loop on humidity sensors
        length_result = len(result[i].get('datapoints'))
        for j in range(0, length_result):  # loop on values
            V = result[i].get('datapoints')[j][0]           # Creat a variable V (voltage)
            result[i].get('datapoints')[j][0] = (0.3524 * V - 0.1554)/(V - 0.3747)  # Calibration equation
            #print result[i].get('datapoints')[j][0]     # Show results


    # ___________________________________________________________________________
    # d. Temperature correction
    """
    Equation:   VWC = VWC + O.OO3 * (Tsensor - Tlab)
    From:       Nemali, Krishna S., Francesco Montesano, Sue K. Dove, and Marc W. van Iersel. 2007. 
                “Calibration and Performance of Moisture Sensors in Soilless Substrates: ECH2O and Theta Probes.” 
                Scientia Horticulturae 112 (2): 227–34. https://doi.org/10.1016/j.scienta.2006.12.013.
    """

    # Parameters
    coef_T = 0.003      # sensitivity to temperature [cm3/cm3/°C]
    Tlab = 22           # lab temperature during calibration [°C]

    # Computation
    for i in range(3):  # loop on humidity sensors
        length_result = len(result[i].get('datapoints'))
        for j in range(0, length_result):   # loop on values
            SWC = result[i].get('datapoints')[j][0]
            Tsensor = result[3].get('datapoints')[j][0]
            result[i].get('datapoints')[j][0] = SWC + coef_T * (Tsensor - Tlab)

    # ___________________________________________________________________________
    # e. Calibration equation

    # ----------------------------------------------------
    # 1. Calibration equation available in the EC-5 datasheet
    """
    Equation:   SWC = (1.3E−03 )(RAW) − 0.696
    From:       METER. n.d. “EC-5 Manual Guide.”
    
    # Parameters
    a = 1.3E-03
    b = -0.696
    HUM_name = ['HUM7', 'HUM8', 'HUM9'] # Humidity sensor's name

    # Computation
    for i in range(3):  # loop on humidity sensors
        length_result = len(result[i].get('datapoints'))
        print HUM_name[i]
        for j in range(0, length_result):  # loop on values
            SWC = result[i].get('datapoints')[j][0]
            result[i].get('datapoints')[j][0] = a * SWC + b  # calculate the real value
            print result[i].get('datapoints')[j][0]
            
    """

    # ----------------------------------------------------
    # 2. Calibration equations determined by experimentation
    """
    Equation:   VWC = a * ln(VWC) + b 
    From:       Experimentation

    # Parameters
    calib = dict()  # Dictionary initialization

    HUM_name = ['HUM7', 'HUM8', 'HUM9'] # Humidity sensor's name
    calib[HUM_name[0]] = [0.4019, 1.2082] # a and b parameters
    calib[HUM_name[1]] = [0.457, 1.2789]
    calib[HUM_name[2]] = [0.4808, 1.3012]

    # Computation
    for i in range(3):  # loop on humidity sensors
        length_result = len(result[i].get('datapoints'))
        print HUM_name[i]
        for j in range(0, length_result):  # loop on values
            SWC = result[i].get('datapoints')[j][0]
            coef = calib.get(HUM_name[i])  # extract the coefficient
            result[i].get('datapoints')[j][0] = coef[0] * SWC + coef[1]  # calculate the real value
            print result[i].get('datapoints')[j][0]
    """

    # ___________________________________________________________________________
    # f. Irrigation

    # calculate the average water content
    theta_mean = []             # Initialization of the list containing mean humidity sensors
    for i in range(3):
        length_result = len(result[i].get('datapoints'))
        theta_sum = 0
        for j in range(0, length_result):
            theta_sum += result[i].get('datapoints')[j][0]
        theta_mean.append(theta_sum / length_result)
    print 'Mean water content [cm3/cm3]:', theta_mean

    # Parameters
    A = 1920                    # box area [cm2]
    H = 12                      # box eight [cm]
    Q = 1000                    # discharge [cm3/hr]
    theta_threshold_box = 0.20  # water content value below which irrigation is switched on in the box [cm3/cm3]
    theta_threshold = [theta_threshold_box, theta_threshold_box, theta_threshold_box]
    theta_fc_box = 0.30         # water content at field capacity in the box [cm3/cm3]
    theta_fc = [theta_fc_box, theta_fc_box, theta_fc_box]

    # Irrigation time
    time_irrig = []
    for i in range(0,len(theta_fc)):
        vol = (theta_fc[i] - theta_threshold[i]) * A * H    # Irrigation volume [cm3]
        time_irrig.append(vol/Q*3600)                       # Irrigation time [s]
        del vol
    print 'time_irrig [s]', time_irrig

    # Find the minimal water content
    index_min = theta_mean.index(min(theta_mean))
    print 'theta_mean min [cm3/cm3]:',theta_mean[index_min]

    # Choose to irrigate or not
    if theta_mean[index_min] < theta_threshold [index_min]:
        timestamp = get_timestamp()
        # erase the current file and open the valve in 30 seconds
        open("valve.txt", 'w').write(str(timestamp + 30) + ";1\n")
        # append to the file and close the valve time_irrig later
        open("valve.txt", 'a').write(str(timestamp + 30 + time_irrig[index_min]) + ";0\n")
        print 'Irrigation is needed'
        print 'Open the valve for', time_irrig[index_min]/3600, 'hour'

    # Processed finished
    print("valve.txt ready.")

    # sleep for 24 hours (in seconds)
    time.sleep(24 * 60)


