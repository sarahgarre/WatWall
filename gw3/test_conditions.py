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
    SD_threshold = 0.03  # Humidity sensor uncertainty[-]

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
    print HUM7_missing

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

    # Check for conditions
    if (
            # NaN values
            all(x == False for x in HUM7_missing) and all(x == False for x in HUM8_missing) and all(x == False for x in HUM9_missing) and
            # Standard deviation
            all(x < SD_threshold for x in V_SD) and
            # Outliers
            all(x > outlier_min for x in HUM7) and all(x > outlier_min for x in HUM8) and all(x > outlier_min for x in HUM9) and
            all(x < outlier_max for x in HUM7) and all(x < outlier_max for x in HUM8) and all(x < outlier_max for x in HUM9)
            ):
        print 'Plan A can be run'
    else:
        print 'Plan A can not be run => Start plan B'


    # sleep for 1 hour (in seconds)
    time.sleep(60 * 60)


