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
#    for index in result:
#       print(index)                   # List of available sensors
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

    # __________________________________________________________________________________________________________________
    # 5.1) reading all values of the last 5 minutes (5 minutes of 60 seconds)

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
        # print(data)                # Display data
        dataFile = urllib.urlopen(url, data, 20)
        result = json.load(dataFile)
        if result:
            # print(result)          # Display results
            for target in result:
                # print target
                index = target.get('target')
                for datapoint in target.get('datapoints'):
                    value = datapoint[0]
                    stamp = datapoint[1] / 1000
                    # print(index + ": " + formatDate(stamp) + " = " + str(value))

    except:
        print(u"URL=" + (url if url else "") + \
              u", Message=" + traceback.format_exc())
    if dataFile:
        dataFile.close()

    # __________________________________________________________________________________________________________________
    # 5.2) Choose to use Plan A or not

    # ---------------------------------------------------------------------------
    # 5.1.1) Parameters

    # Acceptable standard deviation
    SD_threshold = 0.03  # Humidity sensor uncertainty[-]

    # Outliers
    outlier_max = 0.9  # Maximal water content that can be encountered [cm3/cm3]
    outlier_min = 0.3  # Minimal water content that can be encountered [cm3/cm3]

    # --------------------------------------------------------------------------
    # 5.2.2) Calculate indicators

    # ------------------------------
    # Build lists
    HUM7 = []
    HUM8 = []
    HUM9 = []
    TempHum = []
    length_result = len(result[0].get('datapoints'))
    for i in range(0, length_result):
        HUM7.append(result[0].get('datapoints')[i][0])
        HUM8.append(result[1].get('datapoints')[i][0])
        HUM9.append(result[2].get('datapoints')[i][0])
        TempHum.append(result[3].get('datapoints')[i][0])

    print (
        """
############################################
RAW SENSOR'S VALUES
############################################
"""
    )

    print 'HUM7 [V]', HUM7
    print 'HUM8 [V]', HUM8
    print 'HUM9 [V]', HUM9
    print 'TempHum [°C]', TempHum


    # __________________________________________________________________________________________________________________
    # 5.3) Convert raw signal [Volts] in to volumetric water content

    # --------------------------------------------------------------------------
    # 5.3.1) Correct temperature influence on raw signal

    def correctTemp(V_raw, TempHum, Tlab, coef):
        '''
        correctAir corrects signal [volts] with sensor temperature

        Input:
        ------
        Tlab: temperature for which sensors are designed    # [°C]
        V_raw: raw signal                                   # [Volts]
        TempHum: sensor temperature array                   # [°C]
        coef: coefficient of correction                     # [cm3/cm3/°C]
            - 0.0004 : determined empirically
            - 0.003 : Nemali et al., 2007

        Output:
        ------
        V_correct: volumetric water content array           # [Volts]
        '''

        V_correct = V_raw + (TempHum - Tlab) * coef

        return V_correct

    # Temperature for which sensors are designed (Nemali & al., 2007)
    Tlab = 23       # [°C]
    # Correction coefficient (determined empirically)
    coef = 0.0004   # [cm3/cm3/°C]
    # Calculation

    HUM7_correct = []
    HUM8_correct = []
    HUM9_correct = []
    for i in range(0, length_result):
        HUM7_correct.append(correctTemp(HUM7[i], TempHum[i], Tlab, coef))
        HUM8_correct.append(correctTemp(HUM8[i], TempHum[i], Tlab, coef))
        HUM9_correct.append(correctTemp(HUM9[i], TempHum[i], Tlab, coef))

    # --------------------------------------------------------------------------
    # 5.3.2) Convert analogous signal [Volts] into volumetric water content [cm3/cm3]

    def calib(Vraw, eq_type='man_pot'):
        '''
        calib converts the raw signal of an EC-5 sensor with an excitation voltage of 5V to volumetric soil moisture

        Input:
        ------
        Vraw: raw data array
        eq_type: specify which calibration equation you want to use
            CB: Cédric Bernard, 2018 - Zinco substrate
                From: TFE of Cedric Bernard
            meter_2.5V_scaled: METER group manual pot soil equation (scaled)
            licor_5V: calibration equation for 5V excitation
                From:       LICOR, 8100_TechTip_EC-5_Probe_Connection_TTP24.pdf
        Output:
        ------
        VWC: volumetric water content array
        '''
        if eq_type == 'CB':
            VWC = (0.3524 * Vraw - 0.1554) / (Vraw - 0.3747)
        elif eq_type == 'meter_2.5V_scaled':
            VWC = (8.5 * 0.1 * (Vraw / 2)) - 0.24
        elif eq_type == 'licor_5V':
            VWC = (-3.14E-07 * (Vraw/1000)^2) + (1.16E-03 * Vraw/1000) - 6.12E-01
        else:
            VWC = (1.3 * (Vraw / 2)) - 0.348

        return VWC

    # Calibration equation used
    eq_type = 'CB'
    # Calculation
    VWC7 = []
    VWC8 = []
    VWC9 = []
    for i in range(0, length_result):
        VWC7.append(calib(HUM7_correct[i], eq_type))
        VWC8.append(calib(HUM8_correct[i], eq_type))
        VWC9.append(calib(HUM9_correct[i], eq_type))

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

    # __________________________________________________________________________________________________________________
    # 5.4) Irrigation

    # calculate the average water content
    def mean(numbers):
        return float(sum(numbers)) / max(len(numbers), 1)

    theta_mean=[]
    theta_mean.append(mean(VWC7))
    theta_mean.append(mean(VWC8))
    theta_mean.append(mean(VWC9))

    print (
        """
############################################
WATER CONTENT
############################################
"""
    )
    print 'Mean water content [cm3/cm3]:', theta_mean

    # Parameters
    A = 1920  # box area [cm2]
    H = 12  # box eight [cm]
    Q = 1500  # discharge [cm3/hr]

    theta_fc7 = 0.27  # water content at field capacity in the medium of the sensor HUM7 [cm3/cm3]
    theta_fc8 = 0.215  # water content at field capacity in the medium of the sensor HUM8 [cm3/cm3]
    theta_fc9 = 0.255  # water content at field capacity in the medium of the sensor HUM9 [cm3/cm3]

    # Water content at field capacity
    theta_fc = [theta_fc7, theta_fc8, theta_fc9]  # water content at field capacity in the box [cm3/cm3]
    print 'Water content at field capacity [cm3/cm3]:', theta_fc

    # Irrigation time => Water needs in the three layers
    time_irrig = []
    for i in range(0, len(theta_fc)):
        vol = (theta_fc[i] - theta_mean[i]) * A * H  # Irrigation volume [cm3]
        if vol < 0:
            time_irrig.append(0)
        else:
            time_irrig.append(int(vol / Q * 3600))  # Irrigation time [s]
        del vol

    print 'Irrigation time [s]:', time_irrig

    # Find the maximal irrigation time
    index_max = time_irrig.index(max(time_irrig))

    # Irrigation
    timestamp = get_timestamp()
    # erase the current file and open the valve in 30 seconds
    open("valve.txt", 'w').write(str(timestamp + 30) + ";1\n")
    # append to the file and close the valve time_irrig later
    open("valve.txt", 'a').write(str(timestamp + 30 + time_irrig[index_max]) + ";0\n")
    print 'Open the valve for', time_irrig[index_max], 'seconds'

    # Processed finished
    print("valve.txt ready.")

    # Update nohup.out file
    sys.stdout.flush()

    # Update nohup.out file
    sys.stdout.flush()

    # sleep for 24 hours (in seconds)
    time.sleep(24 * 60 * 60)
