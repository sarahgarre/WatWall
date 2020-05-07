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
    # 5.1) Parameters

    # Acceptable standard deviation
    std_threshold = 0.03  # Humidity sensor uncertainty[-]

    # --------------------------------------------------------------------------
    # 5.2) Check for NaN values

    # Build lists
    Vraw7 = []
    Vraw8 = []
    Vraw9 = []
    length_result = len(result[0].get('datapoints'))
    for i in range(0, length_result):
        Vraw7.append(result[0].get('datapoints')[i][0])
        Vraw8.append(result[1].get('datapoints')[i][0])
        Vraw9.append(result[2].get('datapoints')[i][0])
    print 'HUM7 [V]', Vraw7
    print 'HUM8 [V]', Vraw8
    print 'HUM9 [V]', Vraw9

    # Find NaN values
    Vraw7_missing = []
    Vraw8_missing = []
    Vraw9_missing = []
    for i in range(0, length_result):
        Vraw7_missing.append(math.isnan(Vraw7[i]))
        Vraw8_missing.append(math.isnan(Vraw8[i]))
        Vraw9_missing.append(math.isnan(Vraw8[i]))
    print Vraw7_missing

    # --------------------------------------------------------------------------
    # 5.3). Check for outliers

    # build function
    def detect_outlier(list_data, threshold):

        length_list = len(list_data)
        # mean
        mean = math.fsum(list_data)/length_list                 # Compute mean

        # standard deviation
        var = 0                                                     # Initialize variance
        for j in range(0, length_list):
            var += (list_data[i] - mean) ** 2 / length_list     # Compute variance
        std = math.sqrt(var) / mean                             # Compute standard deviation

        outliers = []                                           # Initialize list of outliers
        for y in list_data:                                     # Loop on data
            z_score = (y - mean) / std                          # Compute z-score
            if abs(z_score) > threshold:                        # z-score compared to a threshold
                outliers.append(y)                              # y considered as an outlier
        return outliers

    # Build lists of outliers
    outliers7 = detect_outlier(Vraw7, 3)
    outliers8 = detect_outlier(Vraw8, 3)
    outliers9 = detect_outlier(Vraw9, 3)

    if not outliers7 and not outliers8 and not outliers9:
        print("No outliers detected")
    else:
        print "Outliers detected"

    # Compute number of outliers per list
    NbOut7 = len(outliers7)
    NbOut8 = len(outliers8)
    NbOut9 = len(outliers9)

    # --------------------------------------------------------------------------
    # 5.4) Compute standard deviation

    # mean function
    def std(list_data):

        length_list = len(list_data)
        # mean
        mean = math.fsum(list_data)/length_list                 # Compute mean

        # standard deviation
        var = 0  # Initialize variance
        for j in range(0, length_list):
            var += (list_data[i] - mean) ** 2 / length_list  # Compute variance
        std = math.sqrt(var) / mean  # Compute standard deviation

        return std

    std7 = std(Vraw7)
    std8 = std(Vraw8)
    std9 = std(Vraw9)

    print 'std7 [-]:', std7

    # --------------------------------------------------------------------------
    # 5.4) Compute standard deviation

    # 5.4.1) Check conditions for each sensor
    conditionA = []                                         # List with 1 if OK and 0 if not OK

    # HUM7
    if (
            all(x == False for x in Vraw7_missing) and      # No NaN values
            (std7 < std_threshold) and                      # Standard deviation < threshold
            NbOut7 == 0                                     # No outliers
            ):
        conditionA.append(1)
        print 'HUM7 can be used'
    else:
        conditionA.append(0)
        print 'HUM7 can not be used'

    # HUM8
    if (
            all(x == False for x in Vraw8_missing) and      # No NaN values
            (std8 < std_threshold) and                      # Standard deviation < threshold
            NbOut8 == 0                                     # No outliers
    ):
        conditionA.append(1)
        print 'HUM8 can be used'
    else:
        conditionA.append(0)
        print 'HUM8 can not be used'

    # HUM9
    if (
            all(x == False for x in Vraw9_missing) and      # No NaN values
            (std9 < std_threshold) and                      # Standard deviation < threshold
            NbOut9 == 0                                     # No outliers
    ):
        conditionA.append(1)
        print 'HUM9 can be used'
    else:
        conditionA.append(0)
        print 'HUM9 can not be used'

    # 5.4.2) Choose to use humidity sensors or not
    NbHumMin = 2                                            # Minimal number of operating humidity sensor
    if conditionA.count(1) >= NbHumMin:
        print("Plan A can be run")

        # Irrigate with if conditionA == 1 to only operating sensors
    else:
        print("Go to plan B")


    # sleep for 24 hours (in seconds)
    time.sleep(24 * 60 * 60)
