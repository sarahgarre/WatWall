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
        gr = {'range': {'from': formatDateGMT(now - (24 * 60 * 60)), 'to': formatDateGMT(now)}, \
              'targets': [{'target': 'SDI0'}, {'target': 'SDI1'}, {'target': 'SDI4'}, {'target': 'SDI7'}, {'target': 'SDI8'}, {'target': 'SDI9'}, {'target': 'SDI10'}]}
        data = json.dumps(gr)
        #print(data)
        dataFile = urllib.urlopen(url, data, 20)
        result = json.load(dataFile)
        if result:
            #print(result)
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
    # a. variable conversion

    # global radiation (SDI0): [W/m2] -> [MJ/m2/day]
    index_res=0                                     # Index in the result dict
    Rn = 0                                          # Sum initialization
    length_result = len(result[index_res].get('datapoints'))
    for i in range(0, length_result):
        Rn += 60*result[index_res].get('datapoints')[i][0]     # Calculate sum [J/m2/day]
        # *60 to get the energy per minute [J/min]
    Rn = Rn/(1E06)                                  # Convert units [MJ/m2/day]
    print'Rn=',Rn,'MJ/m2/day'

    # wind speed (SDI4) : mean value over 24 hours [m/s]
    index_res = 2                                           # Index in the result dict
    length_result = len(result[index_res].get('datapoints'))
    u_sum = 0                                               # Sum initialization
    for j in range(0, length_result):
        u_sum += result[index_res].get('datapoints')[j][0]  # Calculate sum [m/s]
    u = u_sum / length_result                               # Calculate mean [m/s]
    print'u =',u,'m/s'

    # temperature (SDI7) : mean value over 24 hours [°C]
    index_res=3                                     # Index in the result dict
    length_result = len(result[index_res].get('datapoints'))
    T_sum = 0                                       # Sum initialization
    for j in range(0, length_result):
        T_sum += result[index_res].get('datapoints')[j][0]  # Calculate sum [°C]
    T = T_sum / length_result                       # Calculate mean [°C]
    print'T =',T,'°C'

    # actual vapor pressure (SDI8) : mean value over 24 hours [kPa]
    index_res = 4                                           # Index in the result dict
    length_result = len(result[index_res].get('datapoints'))
    e_sum = 0  # Sum initialization
    for j in range(0, length_result):
        e_sum += result[index_res].get('datapoints')[j][0]  # Calculate sum [kPa]
    e_a = e_sum / length_result                             # Calculate mean [kPa]
    print'e_a =',e_a,'kPa'

    # atmospheric pressure (SDI9) : mean value over 24 hours [kPa]
    index_res=5                                             # Index in the result dict
    length_result = len(result[index_res].get('datapoints'))
    p_sum = 0                                               # Sum initialization
    for j in range(0, length_result):
        p_sum += result[index_res].get('datapoints')[j][0]  # Calculate sum [kPa]
    p = p_sum / length_result                               # Calculate mean [kPa]
    print'p =',p,'kPa'

    # relative humidity (SDI10) : mean value over 24 hours [%]
    index_res = 6                                           # Index in the result dict
    length_result = len(result[index_res].get('datapoints'))
    RH_sum = 0                                              # Sum initialization
    for j in range(0, length_result):
        RH_sum += result[index_res].get('datapoints')[j][0] # Calculate sum [%]
    RH = RH_sum / length_result                             # Calculate mean [%]
    print'RH =',RH,'%'

    # rain (SDI1) : [mm/hr] -> [mm]
    index_res = 1                                           # Index in the result dict
    length_result = len(result[index_res].get('datapoints'))
    P = 0                                               # Sum initialization
    for j in range(0, length_result):
        P += (result[index_res].get('datapoints')[j][0])/60  # Calculate sum [mm]
    print'P =',P,'mm'

    # ___________________________________________________________________________
    # b. Computation of parameters

    """
    - e_sat: saturation vapour pressure [kPa]
    - gamma: psychrometric constant [kPa/°C]
    - delta: slope of the vapour pressure curve [kPa/°C]
    """

    # saturation vapour pressure [kPa]
    e_sat = 0.6108*math.exp((17.27*T)/(T+273.3))
    print'e_sat =',e_sat,'kPa'
    # psychrometric constant [kPa/°C]
    gamma = 0.665 * p * 1E-03
    print'gamma =',gamma,'kPa/°C'
    # delta [kPa/°C]
    delta = (4098*e_sat)/(T+237.3)**2
    print'delta =',delta,'kPa/°C'

    # ___________________________________________________________________________
    # c. ET0: Daily reference evapotranspiration [mm/day]
    cst = 900
    ET0 = (0.408 * delta * Rn + gamma * cst/(T+273) * u * (e_sat - e_a))/(delta + gamma * (1+0.34*u))
    print 'ET0 =', ET0, 'mm'

    # d. Irrigation

    # Parameters
    A = 1920  # box area [cm2]
    Q = 1000  # discharge [cm3/hr]
    Kc = 1  # cultural coefficient [-]

    # ETc: Daily evapotranspiration [cm/day]
    ET = Kc * ET0 / 10  # Daily evapotranspiration [cm/day]
    time_irrig = int((ET-P/10) * A / Q * 60 * 60)  # Daily watering time [sec] based on ET [cm] and P [cm]
    print'time_irrig=',time_irrig,'seconds'

    # Valve command
    timestamp = get_timestamp()
    # erase the current file and open the valve in 30 seconds
    open("valve.txt", 'w').write(str(timestamp + 30) + ";1\n")
    # append to the file and close the valve time_irrig later
    open("valve.txt", 'a').write(str(timestamp + 30 + time_irrig) + ";0\n")
    print("valve.txt ready.")
    # sleep for 24 hours (in seconds)
    time.sleep(24 * 60 * 60)
