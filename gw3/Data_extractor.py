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
import csv # module for csv files

dstart = int((datetime(2020,5,7,0,0,0)- datetime(1970,1,1)).total_seconds())
dend = int((datetime(2020,5,18,0,0,0)- datetime(1970,1,1)).total_seconds())

print(dstart)
print(dend)

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



# __________________________________________________________________
# a. reading all values of the last 2 months (60 days of 24 hours of 60 minutes of 60 seconds)

"""
sensors' names:
- SDI0 : solar radiation        [W/m2]
- SDI1 : rain                   [mm/h]
- SDI4: wind speed              [m/s]
- SDI5: wind direction          [°]
- SDI7 : air temperature        [°C]
- SDI8: vapor pressure          [kPa]
- SDI9 : atmospheric pressure   [kPa]
- SDI10 : relative humidity     [%]
- VALVE3 : valve state          [0/1]
- HUM7 : first humidity sensor [V]
- HUM8 : second humidity sensor [V]
- HUM9 : third humidity sensor [V]
- SDI11 : humidity sensor temperature [°C]
"""

dataFile = None
try:  # urlopen not usable with "with"
    url = "http://" + host + "/api/grafana/query"
    now = get_timestamp()
    print formatDateGMT(now)
    gr = {'range': {'from': formatDateGMT(dstart), 'to': formatDateGMT(dend)},
          'targets': [{'target': 'SDI0'}, {'target': 'SDI1'}, {'target': 'SDI4'},
                      {'target': 'SDI5'}, {'target': 'SDI7'}, {'target': 'SDI8'},
                      {'target': 'SDI9'}, {'target': 'SDI10'}, {'target': 'VALVE3'},
                      {'target': 'HUM7'}, {'target': 'HUM8'}, {'target': 'HUM9'}, {'target': 'SDI11'}]}
    data = json.dumps(gr)
    #print(data)
    dataFile = urllib.urlopen(url, data, 20)
    result = json.load(dataFile)
    if result:
        #print(result)
        for target in result:
            print target
            #index = target.get('target')
            for datapoint in target.get('datapoints'):
                value = datapoint[0]
                stamp = datapoint[1] / 1000
                #print(index + ": " + formatDate(stamp) + " = " + str(value))
except:
    print(u"URL=" + (url if url else "") + \
          u", Message=" + traceback.format_exc())
if dataFile:
    dataFile.close()

# ___________________________________________________________________________
# a. variable conversion

# Index of the variables in the result dict
index_SolRad = 0            # Global radiation
index_Rain = 1          # Rainfall
index_WindSpeed = 2     # Wind speed
index_WindDirection = 3 # Wind direction
index_TempAir = 4          # Air temperature
index_PressVap = 5            # Vapor pressure
index_PressAtm = 6          # Atmospheric pressure
index_HumRel = 7            # Relative humidity
index_VALVE = 8         # Valve state
index_HUM7 = 9
index_HUM8 = 10
index_HUM9 = 11
index_TempHum = 12

# ------------------------------
# Build lists
# Build lists
Time = []
SolRad = []
Rain = []
WindSpeed = []
WindDirection = []
TempAir = []
PressVap = []
PressAtm = []
HumRel = []
HUM7 = []
HUM8 = []
HUM9 = []
VALVE = []
TempHum = []
length_result = len(result[0].get('datapoints'))
for i in range(0, length_result):
    # Time
    Time.append(formatDateGMT(result[0].get('datapoints')[i][1]/1000))
    # Meteorological data
    SolRad.append(result[0].get('datapoints')[i][0])
    Rain.append(result[1].get('datapoints')[i][0])
    WindSpeed.append(result[2].get('datapoints')[i][0])
    WindDirection.append(result[3].get('datapoints')[i][0])
    TempAir.append(result[index_TempAir].get('datapoints')[i][0])
    PressVap.append(result[index_PressVap].get('datapoints')[i][0])
    PressAtm.append(result[index_PressAtm].get('datapoints')[i][0])
    HumRel.append(result[index_HumRel].get('datapoints')[i][0])
    # Humidity data
    HUM7.append(result[index_HUM7].get('datapoints')[i][0])
    HUM8.append(result[index_HUM8].get('datapoints')[i][0])
    HUM9.append(result[index_HUM9].get('datapoints')[i][0])
    TempHum.append(result[index_TempHum].get('datapoints')[i][0])
    VALVE.append(result[index_VALVE].get('datapoints')[i][0])
    Rain.append(result[index_Rain].get('datapoints')[i][0])
print VALVE

# Open file
m = open("dataELSA_meteo.csv", "w")
v = open("dataELSA_valve.csv", "w")
r = open("dataELSA_rain.csv", "w")
for i in range(0, length_result):
    # Load all meteorological data
    m.write("{},{},{},{},{},{},{},{},{},{},{},{},{},{}\n".format(Time[i], SolRad[i], Rain[i], WindSpeed[i],
                                                                 WindDirection[i], TempAir[i], PressVap[i],
                                                                 PressAtm[i], HumRel[i], HUM7[i], HUM8[i], HUM9[i],
                                                                 TempHum[i], VALVE[i]))
    # Load valve state and rain
    #f.write("{};{};{}\n".format(Time[i], VALVE[i], Rain[i]))

m.close()
v.close()
r.close()

print dstart
print dend
print 'File ready'


