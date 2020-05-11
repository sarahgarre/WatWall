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
    #for index in result:
        #print(index)
except:
    print(u"URL=" + (url if url else "") +
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
    # a. reading all values of the last 24 hours (24 hours of 60 minutes of 60 seconds)

    """
    sensors' names:
    - SDI0 : solar radiation        [W/m2]
    - SDI1 : rain                   [mm/h]
    - SDI4: wind speed              [m/s]
    - SDI7 : air temperature        [°C]
    - SDI8: vapor pressure          [kPa]
    - SDI9 : atmospheric pressure   [kPa]
    - SDI10 : relative humidity     [%]
    """

    dataFile = None
    try:  # urlopen not usable with "with"
        url = "http://" + host + "/api/grafana/query"
        now = get_timestamp()
        gr = {'range': {'from': formatDateGMT(now - (24 * 60 * 60)), 'to': formatDateGMT(now)},
              'targets': [{'target': 'SDI0'}, {'target': 'SDI1'}, {'target': 'SDI4'}, {'target': 'SDI7'},
                          {'target': 'SDI8'}, {'target': 'SDI9'}, {'target': 'SDI10'}]}
        data = json.dumps(gr)
        # print(data)
        dataFile = urllib.urlopen(url, data, 20)
        result = json.load(dataFile)
        if result:
            # print(result)
            for target in result:
                # print target
                index = target.get('target')
                for datapoint in target.get('datapoints'):
                    value = datapoint[0]
                    stamp = datapoint[1] / 1000
                    #print(index + ": " + formatDate(stamp) + " = " + str(value))
                # mean(datapoint[0])
    except:
        print(u"URL=" + (url if url else "") +
              u", Message=" + traceback.format_exc())
    if dataFile:
        dataFile.close()

    # ________________________________________________________________________
    # b. Choose to use Plan B or not

    # ---------------------------------------------------------------------------
    # 5.1) Parameters

    # --------------------------------------------------------------------------
    # 5.2) Check for NaN values

    # Build lists
    solRad = []
    rain = []
    windSpeed = []
    tempAir = []
    pressVap = []
    pressAtm = []
    humRel = []
    length_result = len(result[0].get('datapoints'))
    for i in range(0, length_result):
        solRad.append(result[0].get('datapoints')[i][0])
        rain.append(result[1].get('datapoints')[i][0])
        windSpeed.append(result[2].get('datapoints')[i][0])
        tempAir.append(result[3].get('datapoints')[i][0])
        pressVap.append(result[4].get('datapoints')[i][0])
        pressAtm.append(result[5].get('datapoints')[i][0])
        humRel.append(result[6].get('datapoints')[i][0])
    print (
"""####################################
Sensor values
####################################"""
    )
    print 'Solar radiation [W/m2]:', solRad

    # Find NaN values
    solRad_NaN = []
    rain_NaN = []
    windSpeed_NaN = []
    tempAir_NaN = []
    pressVap_NaN = []
    pressAtm_NaN = []
    humRel_NaN = []
    for i in range(0, length_result):
        solRad_NaN.append(math.isnan(solRad[i]))
        rain_NaN.append(math.isnan(rain[i]))
        windSpeed_NaN.append(math.isnan(windSpeed[i]))
        tempAir_NaN.append(math.isnan(tempAir[i]))
        pressVap_NaN.append(math.isnan(pressVap[i]))
        pressAtm_NaN.append(math.isnan(pressAtm[i]))
        humRel_NaN.append(math.isnan(humRel[i]))

    print (
"""####################################
Presence of NaN values
####################################"""
    )
    print 'Solar radiation:', solRad_NaN.count(True)
    print 'Rain:', rain_NaN.count(True)
    print 'Wind speed:', windSpeed_NaN.count(True)
    print 'Air temperature:', tempAir_NaN.count(True)
    print 'Vapor pressure:', pressVap_NaN.count(True)
    print 'Atmospheric pressure:', pressAtm_NaN.count(True)
    print 'Relative humidity:', humRel_NaN.count(True)

    # 5.5) Can Plan B be used?

    # 5.5.1) Check conditions for each sensor
    conditionB = []  # List with 1 if OK and 0 if not OK
    print (
"""####################################
Are sensor's readings usable?
####################################"""
    )

    # SDI0 : solar radiation
    if (
            all(x == False for x in solRad_NaN)  # No NaN values
    ):
        conditionB.append(1)
        print ' - SDI0 (solar radiation) can be used'
    else:
        conditionB.append(0)
        print ' - SDI0 (solar radiation) can not be used'

    # SDI4: wind speed
    if (
            all(x == False for x in windSpeed_NaN)  # No NaN values
    ):
        conditionB.append(1)
        print ' - SDI4 (wind speed) can be used'
    else:
        conditionB.append(0)
        print ' - SDI4 (wind speed) can not be used'

    # SDI7 : air temperature
    if (
            all(x == False for x in tempAir_NaN) # No NaN values
    ):
        conditionB.append(1)
        print ' - SDI7 (air temperature) can be used'
    else:
        conditionB.append(0)
        print ' - SDI7 (air temperature) can not be used'

    # SDI8: vapor pressure
    if (
            all(x == False for x in pressVap_NaN) # No NaN values
    ):
        conditionB.append(1)
        print ' - SDI8 (vapor pressure) can be used'
    else:
        conditionB.append(0)
        print ' - SDI8 (vapor pressure) can not be used'

    # SDI9 : atmospheric pressure
    if (
            all(x == False for x in pressAtm_NaN) # No NaN values
    ):
        conditionB.append(1)
        print ' - SDI9 (atmospheric pressure) can be used'
    else:
        conditionB.append(0)
        print ' - SDI9 (atmospheric pressure) can not be used'

    # SDI10 : relative humidity
    if (
            all(x == False for x in humRel_NaN) # No NaN values
    ):
        conditionB.append(1)
        print ' - SDI10 (relative humidity) can be used'
    else:
        conditionB.append(0)
        print ' - SDI10 (relative humidity) can not be used'

    # 5.4.2) Choose to use humidity sensors or not
    if all(x == 1 for x in conditionB):
        print("Plan B can be run")
    else:
        print("Go to plan C")

    # sleep for 24 hours (in seconds)
    time.sleep(24 * 60 * 60)
