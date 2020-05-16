#!/usr/bin/env python2
# -*- coding: utf-8 -*-

#_______________________________________________________________________________________________________________________
# DESCRIPTION: Automated irrigation program
# AUTHORS: Groupe 3
user = "GW3"
# Place where the code should run
#test = True     # True to run the code locally
test = False   # False to implement the code on the server

#_______________________________________________________________________________________________________________________
# /!\ PARAMETERS /!\:
# 1) Irrigation system:
irrig_syst = 'pot'          # Irrigation system on Christophe's balcony
#irrig_syst = 'greenwall'   # Greenwall

#_______________________________________________________________________________________________________________________
# PACKAGES

from datetime import datetime
import time
import json
import math
import os, sys
import socket
import traceback
import urllib2 as urllib
import csv

#_______________________________________________________________________________________________________________________
# 0) LINES OF CODE TO SET UP COMMUNICATION WITH THE SERVER AND THE SENSORS
#_______________________________________________________________________________________________________________________

#-----------------------------------------------------------------------------------------------------------------------
# 0.1) Ensure to run in the user home directory

if test:
    host = "greenwall.gembloux.uliege.be"
else:
    host = "localhost"
    # Ensure to run in the user home directory
    DIR_BASE = os.path.expanduser("~")
    if not os.path.samefile(os.getcwd(), DIR_BASE):
        os.chdir(DIR_BASE)
    print(os.getcwd())

#-----------------------------------------------------------------------------------------------------------------------
# 0.2)Ensure to be the only instance to run
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


#-----------------------------------------------------------------------------------------------------------------------
# 0.3) Handling time
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

#-----------------------------------------------------------------------------------------------------------------------
# 0.4) Getting the list of all available sensors

dataFile = None
try:  # urlopen not usable with "with"
    url = "http://" + host + "/api/grafana/search"
    dataFile = urllib.urlopen(url, json.dumps(""), 20)
    result = json.load(dataFile)
    #for index in result:
        #print(index)
except:
    print(u"URL=" + (url if url else "") + \
          u", Message=" + traceback.format_exc())
if dataFile:
    dataFile.close()

#_______________________________________________________________________________________________________________________
# 1) IRRIGATION
#_______________________________________________________________________________________________________________________

# Scheme: collecting sensor readings, taking a decision to irrigate or not and sending the instructions to the valves
# Output: data file with one column with the Linux EPOCH time and valve state (0=closed, 1=opened)

#-----------------------------------------------------------------------------------------------------------------------
# 1.1) Plan A : Irrigation based on humidity sensors readings
#-----------------------------------------------------------------------------------------------------------------------

"""
sensors used:   - HUM7 : first humidity sensor [V]
                - HUM8 : second humidity sensor [V]
                - HUM9 : third humidity sensor [V]
                - SDI7 : air temperature [°C]
"""
print (
"""####################################
PLAN A
####################################"""
    )

while (True):

#-----------------------------------------------------------------------------------------------------------------------
# 1.1.1) Reading humidity sensor values of the last 5 minutes (5 minutes of 60 seconds)

    dataFile = None
    try:  # urlopen not usable with "with"
        url = "http://" + host + "/api/grafana/query"
        now = get_timestamp()
        gr = {'range': {'from': formatDateGMT(now - (1 * 5 * 60)), 'to': formatDateGMT(now)}, \
              'targets': [{'target': 'HUM7'}, {'target': 'HUM8'}, {'target': 'HUM9'}, {'target': 'SDI7'}]}
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
                    #print(index + ": " + formatDate(stamp) + " = " + str(value))

    except:
        print(u"URL=" + (url if url else "") + \
              u", Message=" + traceback.format_exc())
    if dataFile:
        dataFile.close()

    # Build lists
    Vraw7 = []
    Vraw8 = []
    Vraw9 = []
    TempAir = []
    length_result = len(result[0].get('datapoints'))
    for i in range(0, length_result):
        Vraw7.append(result[0].get('datapoints')[i][0])
        Vraw8.append(result[1].get('datapoints')[i][0])
        Vraw9.append(result[2].get('datapoints')[i][0])
        TempAir.append(result[3].get('datapoints')[i][0])

    print '__________________________________'
    print 'Humidity sensor readings (raw values)'

    print 'HUM7 [V]:', Vraw7
    print 'HUM8 [V]:', Vraw8
    print 'HUM9 [V]:', Vraw9

#-----------------------------------------------------------------------------------------------------------------------
# 1.1.2) Choose to use Plan A or not
    # Conditions:   - No NaN values
    #               - No outliers
    #               - Standard deviation lower than humidity sensors uncertainty

    # ---------------------------------------------------------------------------
    # a) Parameters

    # # Minimal number of humidity sensors that meet the conditions
    NbHumMin = 2
    # Humidity sensor uncertainty[-]
    hum_uncert = 0.03

    # --------------------------------------------------------------------------
    # b) Check for NaN values

    # Find NaN values
    Vraw7_NaN = []
    Vraw8_NaN = []
    Vraw9_NaN = []
    TempAir_NaN = []
    for i in range(0, length_result):
        Vraw7_NaN.append(math.isnan(Vraw7[i]))
        Vraw8_NaN.append(math.isnan(Vraw8[i]))
        Vraw9_NaN.append(math.isnan(Vraw8[i]))
        TempAir_NaN.append(math.isnan(TempAir[i]))

    print '__________________________________'
    print 'Presence of NaN values'

    print 'HUM7:', Vraw7_NaN.count(True)
    print 'HUM8:', Vraw8_NaN.count(True)
    print 'HUM9:', Vraw9_NaN.count(True)

    # --------------------------------------------------------------------------
    # c) Check for outliers (z-scores)

    # --------------------------------------------------------------------------
    # d) Compute standard deviation

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
    print '__________________________________'
    print 'Standard deviation'

    print 'Threshold [-]:', hum_uncert
    print 'HUM7:', std7
    print 'HUM8:', std8
    print 'HUM9:', std9

    # --------------------------------------------------------------------------
    # e) Results of the checks

    # Check conditions for each sensor
    conditionA = []                                     # List with 1 if OK and 0 if not OK
    print '____________________________________'
    print "Are humidity sensors' readings usable?"

    # HUM7
    if (
            all(x == False for x in Vraw7_NaN) and      # No NaN values
            (std7 < hum_uncert)                         # Standard deviation < threshold
            ):
        conditionA.append(1)
        print 'HUM7 can be used'
    else:
        conditionA.append(0)
        print 'HUM7 can not be used'

    # HUM8
    if (
            all(x == False for x in Vraw8_NaN) and      # No NaN values
            (std8 < hum_uncert)                         # Standard deviation < threshold
    ):
        conditionA.append(1)
        print 'HUM8 can be used'
    else:
        conditionA.append(0)
        print 'HUM8 can not be used'

    # HUM9
    if (
            all(x == False for x in Vraw9_NaN) and      # No NaN values
            (std9 < hum_uncert)                         # Standard deviation < threshold
    ):
        conditionA.append(1)
        print 'HUM9 can be used'
    else:
        conditionA.append(0)
        print 'HUM9 can not be used'

    # --------------------------------------------------------------------------
    # f) Choose to use humidity sensors or not

    if conditionA.count(1) >= NbHumMin:
        print("=> Plan A can be run")

# -----------------------------------------------------------------------------------------------------------------------
# 1.1.3) Convert analogous signal [Volts] into volumetric water content [cm3/cm3] (if Plan A chosen)

        def calib(Vraw, eq_type):
            '''
            calib converts the raw signal of an EC-5 sensor with an excitation voltage of 5V to volumetric soil moisture

            Input:
            ------
            V_raw: humidity sensor readings array                   [V]
            eq_type: specify which calibration equation is used
                - 'CB': Cédric Bernard, 2018 - Zinco substrate
                  From: TFE of Cedric Bernard
                - 'meter_2.5V_scaled': METER group manual pot soil equation (scaled)
                - 'licor_5V': calibration equation for 5V excitation
                  From: LICOR, 8100_TechTip_EC-5_Probe_Connection_TTP24.pdf
            Output:
            ------
            VWC: volumetric water content array                     [cm3/cm3]
            '''
            if eq_type == 'CB':
                VWC = (0.3524 * Vraw - 0.1554) / (Vraw - 0.3747)
            elif eq_type == 'meter_2.5V_scaled':
                VWC = (8.5 * 0.1 * (Vraw / 2)) - 0.24
            elif eq_type == 'licor_5V':
                VWC = (-3.14E-07 * (Vraw / 1000) ^ 2) + (1.16E-03 * Vraw / 1000) - 6.12E-01
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
            VWC7.append(calib(Vraw7[i], eq_type))
            VWC8.append(calib(Vraw8[i], eq_type))
            VWC9.append(calib(Vraw9[i], eq_type))

        print'__________________________________'
        print'Volumetric water content: calibration equation'
        print 'HUM7 [cm3/cm3]:', VWC7
        print 'HUM8 [cm3/cm3]:', VWC8
        print 'HUM9 [cm3/cm3]:', VWC9

# -----------------------------------------------------------------------------------------------------------------------
# 1.1.4) Correct temperature influence on raw signal (if Plan A chosen)
        # Condition: no NaN values in the humidity sensor temperature array
        if all(x == False for x in TempAir_NaN):

            def correctTemp(VWC, TempAir, sensor):
                '''
                correctTemp corrects VWC  with sensor temperature
                Source: Cobos, Doug, Colin Campbell, and Decagon Devices. n.d. “Correcting Temperature Sensitivity of
                        ECH 2 O Soil Moisture Sensors Strategy 1 : Multiple Regression Analysis,” no. 1.
                ------
                Input:
                VWC: humidity sensor readings array                     [V]
                TempAir: air temperature array                          [°C]
                sensor: sensor name
                    - HUM7
                    - HUM8
                    - HUM9
                ------
                Output:
                VWC_corrected: corrected VWC array                      [cm3/cm3]
                ------
                Equation:
                VWC_corrected = C1* VWC + C2 * TempAir + C3
                '''

                if sensor =='HUM7':
                    C = [0.673092668753705, 0.000174348978687542, 0.0840794823052036]
                elif sensor =='HUM8':
                    C = [0.0326500322594179, -0.000130977585771525, 0.202491414445767]
                elif sensor =='HUM9':
                    C = [0.491143905041849, -0.0000577534352700035, 0.128819057287295]

                VWC_corrected = C[0] * VWC + C[1] * TempAir + C[2]

                return VWC_corrected

            # Calculation
            for i in range(0, length_result):
                VWC7[i] = correctTemp(VWC7[i], TempAir[i], 'HUM7')
                VWC8[i] = correctTemp(VWC8[i], TempAir[i], 'HUM8')
                VWC9[i] = correctTemp(VWC9[i], TempAir[i], 'HUM9')

            print'__________________________________'
            print'Volumetric water content: temperature correction'
            print 'HUM7 [cm3/cm3]:', VWC7
            print 'HUM8 [cm3/cm3]:', VWC8
            print 'HUM9 [cm3/cm3]:', VWC9

        else:
            print'__________________________________'
            print'Volumetric water content: temperature correction'
            print 'NaN detected : TempAir can not be used'


#-----------------------------------------------------------------------------------------------------------------------
# 1.1.5) Irrigation based on humidity sensors (if Plan A chosen)

        print'__________________________________'
        print'Irrigation'

        # calculate the average water content
        def mean(numbers):
            return float(sum(numbers)) / max(len(numbers), 1)

        theta_mean = []
        theta_mean.append(mean(VWC7))
        theta_mean.append(mean(VWC8))
        theta_mean.append(mean(VWC9))

        print 'Mean water content [cm3/cm3]:', theta_mean

        # Parameters
        if irrig_syst == 'pot':
            A_tot = 1920    # box area                      [cm2]
            H_tot = 12      # box height                    [cm]
            Q_tot = 1000    # discharge in the main pipe    [cm3/hr]

            # Heigth
            H7 = H_tot  # height of the first zone          [cm]
            H8 = H_tot  # height of the second zone         [cm]
            H9 = H_tot  # height of the third zone          [cm]
            H = [H7, H8, H9]  # zone height array           [cm]

            # Area of each box zone
            # Each sensor is expected to cover the same horizontal area
            A7 = A_tot/3  # height of the first zone        [cm]
            A8 = A_tot/3  # height of the second zone       [cm]
            A9 = A_tot/3  # height of the third zone        [cm]
            A = [A7, A8, A9]  # zone area array             [cm]

            # Discharge in pipes
            # Discharge is considered identical in the three zones
            Q7 = Q_tot/3  # discharge in the first zone     [cm3/hr]
            Q8 = Q_tot/3  # discharge in the second zone    [cm3/hr]
            Q9 = Q_tot/3  # discharge in the third zone     [cm3/hr]
            Q = [Q7, Q8, Q9]  # discharge array             [cm3/hr]

            # Water content at field capacity
            theta_fc7 = 0.285  # water content at field capacity in the first zone                  [cm3/cm3]
            theta_fc8 = 0.225  # water content at field capacity in the first zone                  [cm3/cm3]
            theta_fc9 = 0.27  # water content at field capacity in the first zone                   [cm3/cm3]
            theta_fc = [theta_fc7, theta_fc8, theta_fc9]  # water content at field capacity array   [cm3/cm3]

        elif irrig_syst == 'greenwall':
            A_tot = 2200 * 13   # wall area                 [cm2]
            H_tot = 107         # wall height               [cm]

            # Heigth
            # The wall is divided into three layers
            H7 = 30     # height of the top layer           [cm]
            H8 = 30     # height of the intermediary layer  [cm]
            H9 = 37     # height of the bottom layer        [cm]
            H = [H7, H8, H9]      # layer height array      [cm]

            # Area
            A7 = A_tot  # area of the top layer             [cm2]
            A8 = A_tot  # area of the intermediary layer    [cm2]
            A9 = A_tot  # area of the bottom layer          [cm2]
            A = [A7, A8, A9]  # layer height array          [cm2]

            # Discharge in pipes
            Q7 = 432000          # discharge in the top layer           [cm3/hr]
            Q8 = 446400          # discharge in the intermediary layer  [cm3/hr]
            Q9 = 460800          # discharge in the bottom layer        [cm3/hr]
            Q = [Q7, Q8, Q9]     # discharge array                      [cm3/hr]

            # Water content at field capacity
            theta_fc7 = 0.285   # water content at field capacity in the first layer                [cm3/cm3]
            theta_fc8 = 0.285   # water content at field capacity in the intermediary layer         [cm3/cm3]
            theta_fc9 = 0.285   # water content at field capacity in the bottom layer               [cm3/cm3]
            theta_fc = [theta_fc7, theta_fc8, theta_fc9]  # water content at field capacity array   [cm3/cm3]

        print 'Water content at field capacity [cm3/cm3]:', theta_fc

        # Irrigation time => Water needs in the three layers
        time_irrig = []
        for i in range(0, len(theta_fc)):
            vol = (theta_fc[i] - theta_mean[i]) * A[i] * H[i]  # Irrigation volume [cm3]
            if vol < 0:
                time_irrig.append(0)
            else:
                time_irrig.append(int(vol / Q[i] * 3600))  # Irrigation time [s]
            del vol

        # Find the maximal irrigation time
        index_OK = [f for f, e in enumerate(conditionA) if e == 1]  # Index of the sensor that meet the conditions
        time_irrigOK = []                                           # Initialization
        for i in range(0, len(index_OK)):
            time_irrigOK.append(time_irrig[index_OK[i]])            # Irrigation time corresponding to sensor that meets the conditions

        index_max = time_irrigOK.index(max(time_irrigOK))           # Index of the maximal irrigation time

        # Irrigation
        timestamp = get_timestamp()
        # erase the current file and open the valve in 30 seconds
        open("valve.txt", 'w').write(str(timestamp + 30) + ";1\n")
        # append to the file and close the valve time_irrig later
        open("valve.txt", 'a').write(str(timestamp + 30 + time_irrigOK[index_max]) + ";0\n")
        print 'Open the valve for', time_irrigOK[index_max], 'seconds'

        # Processed finished
        print("valve.txt ready.")

        # Record action
        if os.path.isfile('history.txt'):  # If file history.txt already exists
            open("history.txt", 'a').write(str(timestamp) + ";A\n")     # Fill file
        else:  # If file history.txt does not exist
            file("history.txt", "w+")                                   # Create file
            open("history.txt", 'a').write(str(timestamp) + ";A\n")     # Fill file

    else:
        print("Go to plan B")

# -----------------------------------------------------------------------------------------------------------------------
# 1.2) Plan B : Irrigation based on ET estimation
# -----------------------------------------------------------------------------------------------------------------------
        print '####################################'
        print 'PLAN B'
        print '####################################'

        """
        sensors used:
        - SDI0 : solar radiation        [W/m2]
        - SDI1 : rain                   [mm/h]
        - SDI4: wind speed              [m/s]
        - SDI7 : air temperature        [°C]
        - SDI8: vapor pressure          [kPa]
        - SDI9 : atmospheric pressure   [kPa]
        - SDI10 : relative humidity     [%]
        """

# -----------------------------------------------------------------------------------------------------------------------
# 1.2.1) Reading sensor values of the last 24 hours (24 hours of 60 minutes of 60 seconds)

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
                        # print(index + ": " + formatDate(stamp) + " = " + str(value))
        except:
            print(u"URL=" + (url if url else "") +
                  u", Message=" + traceback.format_exc())
        if dataFile:
            dataFile.close()

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

        print '____________________________________________'
        print 'Sensor values'
        print 'Solar radiation [W/m2]:', solRad

# -----------------------------------------------------------------------------------------------------------------------
# 1.2.2) Choose to use Plan A or not
# Conditions:   - No NaN values

        # ---------------------------------------------------------------------------
        # a) Parameters

        # --------------------------------------------------------------------------
        # b) Check for NaN values

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

        print '____________________________________________'
        print 'Presence of NaN values'
        print 'Solar radiation:', solRad_NaN.count(True)
        print 'Rain:', rain_NaN.count(True)
        print 'Wind speed:', windSpeed_NaN.count(True)
        print 'Air temperature:', tempAir_NaN.count(True)
        print 'Vapor pressure:', pressVap_NaN.count(True)
        print 'Atmospheric pressure:', pressAtm_NaN.count(True)
        print 'Relative humidity:', humRel_NaN.count(True)

        # --------------------------------------------------------------------------
        # c) Results of the checks

        # Check conditions for each sensor
        conditionB = []  # List with 1 if OK and 0 if not OK
        print '____________________________________'
        print "Are atmospheric sensors' readings usable?"

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
                all(x == False for x in tempAir_NaN)  # No NaN values
        ):
            conditionB.append(1)
            print ' - SDI7 (air temperature) can be used'
        else:
            conditionB.append(0)
            print ' - SDI7 (air temperature) can not be used'

        # SDI8: vapor pressure
        if (
                all(x == False for x in pressVap_NaN)  # No NaN values
        ):
            conditionB.append(1)
            print ' - SDI8 (vapor pressure) can be used'
        else:
            conditionB.append(0)
            print ' - SDI8 (vapor pressure) can not be used'

        # SDI9 : atmospheric pressure
        if (
                all(x == False for x in pressAtm_NaN)  # No NaN values
        ):
            conditionB.append(1)
            print ' - SDI9 (atmospheric pressure) can be used'
        else:
            conditionB.append(0)
            print ' - SDI9 (atmospheric pressure) can not be used'

        # SDI10 : relative humidity
        if (
                all(x == False for x in humRel_NaN)  # No NaN values
        ):
            conditionB.append(1)
            print ' - SDI10 (relative humidity) can be used'
        else:
            conditionB.append(0)
            print ' - SDI10 (relative humidity) can not be used'

        # --------------------------------------------------------------------------
        # d) Choose to use or not atmospheric sensors
        if all(x == 1 for x in conditionB):
            print("Plan B can be run")

# -----------------------------------------------------------------------------------------------------------------------
# 1.2.3) Convert variables for Penman equation
            print '____________________________________________'
            print 'Data conversion for Penman equation'

            # global radiation (SDI0): [W/m2] -> [MJ/m2/day]
            Rn = 0                                                  # Sum initialization
            Rn_list = []
            length_result = len(result[0].get('datapoints'))
            for i in range(0, length_result):
                Rn += 60 * solRad[i]                                # Calculate sum [J/m2/day]
                                                                    # *60 to get the energy per minute [J/min]
            Rn = Rn / (1E06)                                        # Convert units [MJ/m2/day]
            print'Rn =', Rn, 'MJ/m2/day'

            # wind speed (SDI4) : mean value over 24 hours [m/s]
            u_sum = 0                                               # Sum initialization
            for i in range(0, length_result):
                u_sum += windSpeed[i]                               # Calculate sum [m/s]
            u = u_sum / length_result                               # Calculate mean [m/s]
            print'u =', u, 'm/s'

            # temperature (SDI7) : mean value over 24 hours [°C]
            T_sum = 0                                               # Sum initialization
            for i in range(0, length_result):
                T_sum += tempAir[i]                                 # Calculate sum [°C]
            T = T_sum / length_result                               # Calculate mean [°C]
            print'T =', T, '°C'

            # actual vapor pressure (SDI8) : mean value over 24 hours [kPa]
            e_sum = 0                                               # Sum initialization
            for i in range(0, length_result):
                e_sum += pressVap[i]                                # Calculate sum [kPa]
            e_a = e_sum / length_result                             # Calculate mean [kPa]
            print'e_a =', e_a, 'kPa'

            # atmospheric pressure (SDI9) : mean value over 24 hours [kPa]
            p_sum = 0                                               # Sum initialization
            for i in range(0, length_result):
                p_sum += pressAtm[i]                                # Calculate sum [kPa]
            p = p_sum / length_result                               # Calculate mean [kPa]
            print'p =', p, 'kPa'

            # relative humidity (SDI10) : mean value over 24 hours [%]
            RH_sum = 0                                              # Sum initialization
            for i in range(0, length_result):
                RH_sum += humRel[i]                                 # Calculate sum [%]
            RH = RH_sum / length_result                             # Calculate mean [%]
            print'RH =', RH, '%'

            # rain (SDI1) : [mm/hr] -> [mm]
            P = 0                                                   # Sum initialization
            for i in range(0, length_result):
                P += rain[i] / 60                                   # Calculate sum [mm]
            print'P =', P, 'mm'

# -----------------------------------------------------------------------------------------------------------------------
# 1.2.4) Calculate parameters of Penman equation

            """
            - e_sat: saturation vapour pressure [kPa]
            - gamma: psychrometric constant [kPa/°C]
            - delta: slope of the vapour pressure curve [kPa/°C]
            """
            print '____________________________________________'
            print 'Parameters of Penman equation'

            # saturation vapour pressure [kPa]
            e_sat = 0.6108 * math.exp((17.27 * T) / (T + 273.3))
            print'e_sat =', e_sat, 'kPa'
            # psychrometric constant [kPa/°C]
            gamma = 0.665 * p * 1E-03
            print'gamma =', gamma, 'kPa/°C'
            # delta [kPa/°C]
            delta = (4098 * e_sat) / (T + 237.3) ** 2
            print'delta =', delta, 'kPa/°C'

# -----------------------------------------------------------------------------------------------------------------------
# 1.2.5) Estimate ET

            print '____________________________________________'
            print 'ET estimation of the previous day'

            # ET0
            cst = 900
            ET0 = (0.408 * delta * Rn + gamma * cst / (T + 273) * u * (e_sat - e_a)) / (delta + gamma * (1 + 0.34 * u))
            print 'ET0 =', ET0, 'mm/day'

            # Kc
            if irrig_syst == 'pot':
                Kc = 0.5    # cultural coefficient of rocket [-]
            elif irrig_syst == 'greenwall':
                Kc = 0.6    # global cultural coefficient of the wall [-]

            # Etc
            ET = Kc * ET0    # Daily evapotranspiration [mm/day]
            print 'ETc =', ET, 'mm/day'

# -----------------------------------------------------------------------------------------------------------------------
# 1.2.6) Irrigation

            print'__________________________________'
            print'Irrigation'

            if irrig_syst == 'pot':
                # Parameters
                A_rain_tot = 1920   # rainfall area                                 [cm2]
                A_ET_tot = A_rain_tot   # ET area                                   [cm2]
                Q_tot = 1000    # discharge in the main pipe                        [cm3/hr]

                # Rainfall area
                A_rain7 = A_rain_tot/3  # rainfall area of the first zone           [cm2]
                A_rain8 = A_rain_tot/3  # rainfall area of the second zone          [cm2]
                A_rain9 = A_rain_tot/3  # rainfall area of the third zone           [cm2]
                A_rain = [A_rain7, A_rain8, A_rain9]  # zone rainfall area array    [cm2]

                # ET area
                A_ET7 = A_ET_tot / 3  # ET area of the first zone                   [cm2]
                A_ET8 = A_ET_tot / 3  # ET area of the second zone                  [cm2]
                A_ET9 = A_ET_tot / 3  # ET area of the third zone                   [cm2]
                A_ET = [A_ET7, A_ET8, A_ET9]  # zone ET area array                  [cm2]

                # Discharge in pipes
                # Discharge is considered identical in the three zones
                Q7 = Q_tot / 3  # discharge in the first zone                       [cm3/hr]
                Q8 = Q_tot / 3  # discharge in the second zone                      [cm3/hr]
                Q9 = Q_tot / 3  # discharge in the third zone                       [cm3/hr]
                Q = [Q7, Q8, Q9]  # discharge array                                 [cm3/hr]

            elif irrig_syst == 'greenwall':
                # Parameters
                A_rain_tot = 220*13    # rainfall area (top)                            [cm2]
                A_cell = 10 * 10    # wall cell area                                    [cm2]
                cell_Nb = 26 * 10   # wall cell number                                  [cm2]
                A_ET_tot = A_rain_tot + A_cell*cell_Nb   # ET area                      [cm2]
                H_tot = 107    # wall height                                            [cm]

                # Rainfall area
                A_rain7 = A_rain_tot      # rainfall area of the top layer              [cm2]
                A_rain8 = 0               # rainfall area of the intermediary layer     [cm2]
                A_rain9 = 0               # rainfall area of the bottom layer           [cm2]
                A_rain = [A_rain7, A_rain8, A_rain9]  # layer rainfall area array       [cm2]

                # Heigth
                # The wall is divided into three layers
                H7 = 30  # height of the top layer                                      [cm]
                H8 = 30  # height of the intermediary layer                             [cm]
                H9 = 37  # height of the bottom layer                                   [cm]
                H = [H7, H8, H9]  # layer height array                                  [cm]

                # ET area
                A_ET7 = A_ET_tot * H7/H_tot     # ET area of the top layer              [cm2]
                A_ET8 = A_ET_tot * H8/H_tot     # ET area of the intermediary layer     [cm2]
                A_ET9 = A_ET_tot * H9/H_tot     # ET area of the bottom layer           [cm2]
                A_ET = [A_ET7, A_ET8, A_ET9]       # layer ET area array                   [cm2]

                # Discharge in pipes
                Q7 = 432000  # discharge in the top layer                               [cm3/hr]
                Q8 = 446400  # discharge in the intermediary layer                      [cm3/hr]
                Q9 = 460800  # discharge in the bottom layer                            [cm3/hr]
                Q = [Q7, Q8, Q9]  # discharge array                                     [cm3/hr]

            # Irrigation time => Water needs in the three layers
            time_irrig = []
            for i in range(0, len(Q)):
                vol = ET/10 * A_ET[i] - P/10 * A_rain[i]                       # Irrigation volume [cm3]
                if vol < 0:
                    time_irrig.append(0)
                else:
                    time_irrig.append(int(vol / Q[i] * 3600))  # Irrigation time [s]
                del vol

            # Find the maximal irrigation time
            index_max = time_irrig.index(max(time_irrig))  # Index of the maximal irrigation time

            # Valve command
            timestamp = get_timestamp()
            # erase the current file and open the valve in 30 seconds
            open("valve.txt", 'w').write(str(timestamp + 30) + ";1\n")
            # append to the file and close the valve time_irrig later
            open("valve.txt", 'a').write(str(timestamp + 30 + time_irrig[index_max]) + ";0\n")
            print 'Open the valve for', time_irrig[index_max], 'seconds'

            print("valve.txt ready.")

            # Record action
            if os.path.isfile('history.txt'):  # If file history.txt already exists
                open("history.txt", 'a').write(str(timestamp) + ";B\n")  # Fill file
            else:  # If file history.txt does not exist
                file("history.txt", "w+")  # Create file
                open("history.txt", 'a').write(str(timestamp) + ";B\n")  # Fill file

        else:
            print("Go to plan C")

# -----------------------------------------------------------------------------------------------------------------------
# 1.3) Plan C : Irrigation based on ET estimated with previous years' data
# -----------------------------------------------------------------------------------------------------------------------
            print '####################################'
            print 'PLAN C'
            print '####################################'

            # Kc
            if irrig_syst == 'pot':
                Kc = 0.5  # cultural coefficient of rocket [-]
            elif irrig_syst == 'greenwall':
                Kc = 0.6  # global cultural coefficient of the wall [-]

            # Discharge and surfaces
            if irrig_syst == 'pot':
                # Parameters
                A_ET_tot = 1920   # ET area                                         [cm2]
                Q_tot = 1000    # discharge in the main pipe                        [cm3/hr]

                # ET area
                A_ET7 = A_ET_tot / 3  # ET area of the first zone                   [cm2]
                A_ET8 = A_ET_tot / 3  # ET area of the second zone                  [cm2]
                A_ET9 = A_ET_tot / 3  # ET area of the third zone                   [cm2]
                A_ET = [A_ET7, A_ET8, A_ET9]  # zone ET area array                  [cm2]

                # Discharge in pipes
                # Discharge is considered identical in the three zones
                Q7 = Q_tot / 3  # discharge in the first zone                       [cm3/hr]
                Q8 = Q_tot / 3  # discharge in the second zone                      [cm3/hr]
                Q9 = Q_tot / 3  # discharge in the third zone                       [cm3/hr]
                Q = [Q7, Q8, Q9]  # discharge array                                 [cm3/hr]

            elif irrig_syst == 'greenwall':
                # Parameters
                A_cell = 10 * 10    # wall cell area                                    [cm2]
                cell_Nb = 26 * 10   # wall cell number                                  [cm2]
                A_ET_tot = 220 * 13 + A_cell*cell_Nb   # ET area                        [cm2]
                H_tot = 107    # wall height                                            [cm2]

                # Heigth
                # The wall is divided into three layers
                H7 = 30  # height of the top layer                                      [cm]
                H8 = 30  # height of the intermediary layer                             [cm]
                H9 = 37  # height of the bottom layer                                   [cm]
                H = [H7, H8, H9]  # layer height array                                  [cm]

                # ET area
                A_ET7 = A_ET_tot * H7/H_tot     # ET area of the top layer              [cm2]
                A_ET8 = A_ET_tot * H8/H_tot     # ET area of the intermediary layer     [cm2]
                A_ET9 = A_ET_tot * H9/H_tot     # ET area of the bottom layer           [cm2]
                A_ET = [A_ET7, A_ET8, A_ET9]    # layer ET area array                   [cm2]

                # Discharge in pipes
                Q7 = 432000  # discharge in the top layer                               [cm3/hr]
                Q8 = 446400  # discharge in the intermediary layer                      [cm3/hr]
                Q9 = 460800  # discharge in the bottom layer                            [cm3/hr]
                Q = [Q7, Q8, Q9]  # discharge array                                     [cm3/hr]

            # ET0 file of Gembloux
            file = open("ET0_2010_2019.csv", "r")  # open the file
            reader = csv.reader(file, delimiter=";")  # file reading initialization

            # Skip the first two lines
            next(reader)
            next(reader)

            outfile = open('valve.txt', 'w')

            # Transform date into epoch time
            for row in reader:  # loop to go through the reader
                #print (row[0])  # display rows

                # Convert datetime into epoch
                hiredate = row[0]  # select date in the list
                pattern = '%d/%m/%Y %H:%M'  # date format
                epoch = int(time.mktime(time.strptime(hiredate, pattern)))  # convert date to epoch time
                #print epoch

                # Get ET0
                ET0 = float(row[1])     # Daily reference evapotranspiration        [mm/day]

                # Compute ETc
                ET = Kc * ET0           # Daily evapotranspiration                  [mm/day]

                # Irrigation time => Water needs in the three layers
                time_irrig = []
                for i in range(0, len(theta_fc)):
                    vol = ET / 10 * A_ET[i]  # Irrigation volume                    [cm3]
                    if vol < 0:
                        time_irrig.append(0)
                    else:
                        time_irrig.append(int(vol / Q[i] * 3600))  # Irrigation time [s]
                    del vol

                # Find the maximal irrigation time
                index_max = time_irrig.index(max(time_irrig))  # Index of the maximal irrigation time

                # open the valve
                outfile.write(str(epoch + 24 * 60 * 60) + ";1\n")
                # append to the file and close the valve the next day (+ 24*60*60) at 00:00 + time_irrig
                outfile.write(str(epoch + 24 * 60 * 60 + time_irrig[index_max]) + ";0\n")

            outfile.close()  # close valve.txt
            print("valve.txt ready.")
            file.close()  # close the file

            # Record action
            timestamp = get_timestamp()
            if os.path.isfile('history.txt'):   # If file history.txt already exists
                open("history.txt", 'a').write(str(timestamp) + ";C\n")      # Fill file
            else:                               # If file history.txt does not exist
                file("history.txt", "w+")                                    # Create file
                open("history.txt", 'a').write(str(timestamp) + ";C\n")      # Fill file

    # Update nohup.out file
    sys.stdout.flush()

    # sleep for 24 hours (in seconds)
    time.sleep(24 * 60 * 60)
