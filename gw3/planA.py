#!/usr/bin/env python2
# -*- coding: utf-8 -*-

# Packages of Christophe

from datetime import datetime
import time
import calendar
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

    # create mean function
    def mean(numbers):
        return float(sum(numbers)) / max(len(numbers), 1)


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
                # mean(datapoint[0])
    except:
        print(u"URL=" + (url if url else "") + \
              u", Message=" + traceback.format_exc())
    if dataFile:
        dataFile.close()

    # ___________________________________________________________________________
    # b. Temperature correction

    # temperature correction
    coef_T = 0.003  # sensitivity to temperature [cm3/cm3/°C]
    Tlab = 22  # lab temperature during calibration [°C]

    for i in range(3):
        length_result = len(result[i].get('datapoints'))
        for j in range(0, length_result):
            result[i].get('datapoints')[j][0] = result[i].get('datapoints')[j][0] + coef_T * (result[3].get('datapoints')[j][0]) - Tlab)

    # ___________________________________________________________________________
    # c. Calculate mean and standard deviation

    # calculate the average water content
    theta_mean = []
    for i in range(3):
        length_result = len(result[i].get('datapoints'))
        theta_sum = 0
        for j in range(0, length_result):
            theta_sum += result[i].get('datapoints')[j][0]
        theta_mean.append(theta_sum / length_result)
    print(theta_mean)

    # calculate the standard deviation
    theta_SD = []
    for i in range(3):
        length_result = len(result[i].get('datapoints'))
        theta_diff = 0
        for j in range(0, length_result):
            theta_diff += (result[i].get('datapoints')[j][0] - theta_mean[i]) ** 2
        theta_SD.append(math.sqrt(theta_diff / length_result))
    print(theta_SD)

    # ___________________________________________________________________________
    # d. detecting outliers

    # Parameters
    SD_threshold = 0.05  # Maximum standard deviation accepted

    # NaN values
    math.isnan(value)

    # ___________________________________________________________________________
    # e. Calibration equations

    calib = dict()  # Dictionary initialization

    HUM_name=['HUM7', 'HUM8', 'HUM9']
    calib[HUM_name[0]] = [0.4019, 1.2082]
    calib[HUM_name[1]] = [0.457, 1.2789]
    calib[HUM_name[2]] = [0.4808, 1.3012]

    for i in range(len(theta_mean)):
        theta_mean[i] = math.log(theta_mean[i])             # take the natural logarithm
        print(theta_mean[i])
        coef = calib.get(HUM_name[i])                       # extract the coefficient
        print(coef)
        theta_mean[i] = coef[0] * theta_mean[i] + coef[1]   # calculate the real value
        print(theta_mean[i])

    # _____________________________________________________________________________
    # writing the valve.txt file
    timestamp = get_timestamp()
    # erase the current file and open the valve in 30 seconds
    open("valve.txt", 'w').write(str(timestamp + 30) + ";1\n")
    # append to the file and close the valve 1 minute later
    open("valve.txt", 'a').write(str(timestamp + 90) + ";0\n")
    print("valve.txt ready.")
    # sleep for 5 minutes (in seconds)
    time.sleep(5 * 60)
