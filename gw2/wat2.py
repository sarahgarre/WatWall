#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from datetime import datetime
import time
import calendar
import json
import math
import os, sys
import socket
import traceback
import urllib2 as urllib

user = "GW1"
test = True

if test:
    host = "greenwall.gembloux.uliege.be"
    print('Script running  on ''local'' mode')
else:
    print('Script running on ''network'' mode')
    host = "localhost"
    # Ensure to run in the user home directory
    DIR_BASE = os.path.expanduser("~")
    if not os.path.samefile(os.getcwd(), DIR_BASE):
        os.chdir(DIR_BASE)
    print(os.getcwd())

    # Ensure to be the only instance to run
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


# EPOCH time is the number of seconds since 1/1/1970
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

# Getting the list of all available sensors
#dataFile = None
#try:  # urlopen not usable with "with"
#    url = "http://" + host + "/api/grafana/search"
#    dataFile = urllib.urlopen(url, json.dumps(""), 20)
#    result = json.load(dataFile)
#   print('Here is the list of available sensors')
#    for index in result:
#        print(index)
#except:
#    print(u"URL=" + (url if url else "") + \
#          u", Message=" + traceback.format_exc())
#if dataFile:
#    dataFile.close()

# Your program must create a data file with one column with the Linux EPOCH time and your valve state
# (0=closed, 1=opened)

while (True):

    # Example reading last sensor value
    # dataFile = None
    # try:  # urlopen not usable with "with"
    #    url = "http://" + host + "/api/get/%21s_HUM1"
    #    dataFile = urllib.urlopen(url, None, 20)
    #    data = dataFile.read(80000)
    #    print("HUM1=" + data.strip(delimiters))
    # except:
    #    print(u"URL=" + (url if url else "") + \
    #          u", Message=" + traceback.format_exc())
    # if dataFile:
    #    dataFile.close()

    # Example reading all values of the last hour (60 minutes of 60 seconds)
    dataFile = None
    try:  # urlopen not usable with "with"
        url = "http://" + host + "/api/grafana/query"
        now = get_timestamp()
        gr = {'range': {'from': formatDateGMT(now - (24 * 60 * 60)), 'to': formatDateGMT(now)}, \
              'targets': [{'target': 'HUM4'}, {'target': 'HUM5'}, {'target': 'HUM6'}, {'target': 'SDI0'},
                          {'target': 'SDI1'}, {'target': 'SDI4'}, {'target': 'SDI7'}, {'target': 'SDI8'},
                          {'target': 'SDI9'}, {'target': 'SDI10'}]}
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
        print(u"URL=" + (url if url else "") + \
              u", Message=" + traceback.format_exc())
    if dataFile:
        dataFile.close()

    # calcul de la valeur moyenne des HUMX dans la dernière heure -> averageHUMX
    somme1 = 0
    somme2 = 0
    somme3 = 0
    for i in range(0, len(result[0].get('datapoints'))):
        somme1 = somme1 + result[0].get('datapoints')[i][0]
        somme2 = somme2 + result[1].get('datapoints')[i][0]
        somme3 = somme3 + result[2].get('datapoints')[i][0]
    averageHUM4 = somme1 / len(result[0].get('datapoints'))
    averageHUM5 = somme2 / len(result[0].get('datapoints'))
    averageHUM6 = somme3 / len(result[0].get('datapoints'))
    # print averageHUM4
    # print averageHUM5
    # print averageHUM6

    # calcul de la moyenne des 3 sondes -> averageHUM456
    averageHUM456 = (averageHUM4 + averageHUM5 + averageHUM6) / 3
    # print averageHUM456

    # calibration page 18 http://manuals.decagon.com/Retired%20and%20Discontinued/Manuals/EC-20-EC-10-EC-5-Soil-Moisture-Sensor-Operators-Manual-(discontinued).pdf
    VWC = 1.3 * averageHUM456 - 0.696

    ## QUALIY CHECK

    # 1/ Set number of successive values to consider
    # TODO : set number of successive data points to consider
    N = 5

    # 2/ Set admissible std (INSERT TRUE VALUE)
    # TODO : set admissible std for each sensor

    LIM_HUM4 = 1
    LIM_HUM5 = 1
    LIM_HUM6 = 1
    LIM_Rn = 1
    LIM_Thr = 1
    LIM_u2 = 1
    LIM_P = 1

    # 3/ computation of std for water content probes

    length_result = len(result[0].get('datapoints'))
    for i in range(length_result - N, length_result):  # pour les N dernières mesures de la journée
        SCE_HUM4 = pow((result[0].get('datapoints')[i][0] - averageHUM4),2)  # calcul de la somme des carrés des écarts pour HUM4
        SCE_HUM5 = pow((result[1].get('datapoints')[i][0] - averageHUM5),2)  # calcul de la somme des carrés des écarts pour HUM5
        SCE_HUM6 = pow((result[2].get('datapoints')[i][0] - averageHUM6),2)  # calcul de la somme des carrés des écarts pour HUM6
    std_HUM4 = math.sqrt((1 / N) * SCE_HUM4)  # calcul du std (écart type)
    std_HUM5 = math.sqrt((1 / N) * SCE_HUM5)  # calcul du std (écart type)
    std_HUM6 = math.sqrt((1 / N) * SCE_HUM6)  # calcul du std (écart type)

    # 4/ computation of std for weather station data

    # pre allocations
    length_result = len(result[0].get('datapoints'))
    sum_Rn = 0
    sum_Thr = 0
    sum_u2 = 0
    sum_P = 0

    # Compute sum & mean
    for i in range(length_result - N, length_result):  # pour les N dernières mesures de la journée
        sum_Rn = sum_Rn + result[3].get('datapoints')[i][0]  # sum of data points
        sum_Thr = sum_Thr + result[6].get('datapoints')[i][0]
        sum_u2 = sum_u2 + result[5].get('datapoints')[i][0]
    mean_Rn = sum_Rn / N
    mean_Thr = sum_Thr / N
    mean_u2 = sum_u2 / N

    length_result = len(result[8].get('datapoints'))
    for i in range(length_result - N, length_result):  # pour les N dernières mesures de la journée
        sum_P = sum_P + result[8].get('datapoints')[i][0]
    mean_P = sum_P / N

    for i in range(length_result - N, length_result):  # pour les N dernières mesures de la journée
        SCE_Rn = pow((result[3].get('datapoints')[i][0] - mean_Rn), 2)  # calcul de la somme des carrés des écarts
        SCE_Thr = pow((result[6].get('datapoints')[i][0] - mean_Thr), 2)
        SCE_u2 = pow((result[5].get('datapoints')[i][0] - mean_u2), 2)
        SCE_P = pow((result[8].get('datapoints')[i][0] - mean_P), 2)
    std_Rn = math.sqrt((1 / N) * SCE_Rn)  # calcul du std (écart type)
    std_Thr = math.sqrt((1 / N) * SCE_Thr)
    std_u2 = math.sqrt((1 / N) * SCE_u2)
    std_P = math.sqrt((1 / N) * SCE_P)

    ## IRRIGATION DECISION

# 1/  Quality check for all 3 WC sensor
    print('Checking sensors :')
    if std_HUM4 < LIM_HUM4 and std_HUM5 < LIM_HUM5 and std_HUM6 < LIM_HUM6:
        HUM_QualCheck = True
        print('* Water content probe working')
    else:
        HUM_QualCheck = False
        print('* Water content probe NOT working')

    # 2/ Quality check for weather station data
    if std_Rn < LIM_Rn and std_Thr < LIM_Thr and std_u2 < LIM_u2 and std_P < LIM_P:
        WS_QualCheck = True
        print('* Weather station working')
    else:
        WS_QualCheck = False
        print('* Weather station NOT working')

    # 3/ Check whether irrigation is needed
    # TODO : set minimum water content bellow which irrig is triggered

    # Set minimum water content admissible
    Water_Content_Limit = 1

    # Irrigation decision
    print('Irrigation will start if water content is lower than :')
    print('    ...Still to set !')

    if VWC < Water_Content_Limit:
        Irrig_Needed = True
        print('Irrigation is needed')
    else:
        Irrig_Needed = False
        print('Irrigation is NOT needed')

    # IRRIGATION BASED ON WS STARTS :

    # Ici on effectue le calcul d'ET0 pour chaque heure durant les dernières 24h

    if HUM_QualCheck == True and Irrig_Needed == True and WS_QualCheck == True:

        print('Irrigation based on weather station data starts')

        SommeRn = range(23)
        Thr = range(23)
        eThr = range(23)
        ea = range(23)
        u2 = range(23)
        delta = range(23)
        P = range(23)
        gamma = range(23)
        ET0 = range(23)
        Pluie = range(23)

        for j in range(0, 23):

            # calcul de la somme des irradiations pour chaque heure -> Rn [MJ/(m2 hour)]
            somme = 0
            a = 0
            length_result = len(result[3].get('datapoints'))
            for i in range(length_result - (60 * 24) + (j * 60) + 1, length_result - ((23 - j) * 60)):
                somme = somme + result[3].get('datapoints')[i][0] * 60 / (10 ** 6)
            SommeRn[j] = somme

            # calcul de la température moyenne pour chaque heure -> Thr [°C]
            somme = 0
            length_result = len(result[6].get('datapoints'))
            for i in range(length_result - (60 * 24) + (j * 60) + 1, length_result - ((23 - j) * 60)):
                somme = somme + result[6].get('datapoints')[i][0]
            Thr[j] = somme / 60

            # calcul de la pression de vapeur saturante pour chaque heure par l'équation August-Roche-Magnus -> eThr [kPa]
            # (https://en.wikipedia.org/wiki/Vapour_pressure_of_water)
            eThr[j] = 0.61094 * math.exp(17.625 * Thr[j] / (Thr[j] + 243.04))

            # calcul de la pression de vapeur réele -> ea [kPa]
            somme = 0
            length_result = len(result[7].get('datapoints'))
            for i in range(length_result - (60 * 24) + (j * 60) + 1, length_result - ((23 - j) * 60)):
                somme = somme + result[7].get('datapoints')[i][0]
            ea[j] = somme / 60

            # calcul de la vitesse moyenne du vent pour chaque heure -> u2 [m/s]
            somme = 0
            length_result = len(result[5].get('datapoints'))
            for i in range(length_result - (60 * 24) + (j * 60) + 1, length_result - ((23 - j) * 60)):
                somme = somme + result[5].get('datapoints')[i][0]
            u2[j] = somme / 60
            # u2 = 0.01

            # calcul de la pente de la courbe de pression de vapeur à saturation -> delta [kPa /°C]
            delta[j] = 1635631.478 * math.exp(3525 * Thr[j] / (200 * Thr[j] + 48608)) / (25 * Thr[j] + 6076) ** 2

            # calcul de la pression atmosphérique moyenne pour chaque heure -> P [kPa]
            somme = 0
            length_result = len(result[8].get('datapoints'))
            for i in range(length_result - (60 * 24) + (j * 60) + 1, length_result - ((23 - j) * 60)):
                somme = somme + result[8].get('datapoints')[i][0]
            P[j] = somme / 60

            # calcul de la constante psychrométrique -> gamma [kPa/°C] https://en.wikipedia.org/wiki/Psychrometric_constant
            Cp = 0.001005  # Specific Heat Capacities of Air at 300 K [MJ/Kg K]
            # https://www.ohio.edu/mechanical/thermo/property_tables/air/air_Cp_Cv.html
            lambdav = 2.26  # Latent heat of water vaporization [MJ / kg]
            MW_ratio = 0.622  # Ratio molecular weight of water vapor/dry air
            gamma[j] = Cp * P[j] / (lambdav * MW_ratio)

            # formule ET0 [mm/hour]
            ET0[j] = (0.408 * delta[j] * SommeRn[j] + gamma[j] * (37 / (Thr[j] + 273)) * u2[j] * (eThr[j] - ea[j])) / (
                    delta[j] + gamma[j] * (1 + 0.34 * u2[j]))

            # Crop coefficient [Temporaire]
            # TODO : set acctual crop coefficient
            Kl = 0.7

            # Dimensions du pot -> Area [m2]
            Area = 0.75 * 0.14

            # Pluie durant chaque heure -> Pluie [L]
            somme = 0
            length_result = len(result[4].get('datapoints'))
            for i in range(length_result - (60 * 24) + (j * 60) + 1, length_result - ((23 - j) * 60)):
                Pluvio = somme + result[4].get('datapoints')[i][
                    0] / 60  # on divise par 60 car on cumule des intensités de pluie
                Pluie[j] = Pluvio * Area  # exprimées en mm/h

        print "Yesterday it rained", round(sum(Pluie), 3), "litres on our pot"
        print "The ET0 for yesterday was", round(sum(ET0), 3), "mm."

        # Calcul de dose à appliquer pour chaque heure [L]
        Dosis = sum(ET0) * Kl * Area - sum(Pluie)
        if Dosis < 0:
            Dosis = 0
        else:
            Dosis = Dosis
        print "The dosis of water to apply today is ", round(Dosis, 3), "L."

        # calcul du temps d'ouverture de la valve -> t [min]
        Q = 1.5 / 60  # L/min
        t = Dosis / Q
        print "Today we need to open the valve for", round(t, 2), " minutes"

        timestamp = get_timestamp()
        # erase the current file and open the valve in 30 seconds
        open("valve.txt", 'w').write(str(timestamp + 30) + ";1\n")
        # append to the file and close the valve 1 minute later
        open("valve.txt", 'a').write(str(timestamp + t + 30) + ";0\n")
        print("Irrigation has been processed")

        # sleep for irrigation time PLUS x hours
        # TODO : Set waiting time between first irrigation and post-irrig check
        waiting_time = 60*2

        time.sleep(t + 60 * waiting_time)


    ## POST IRRIGATION CHECK

    if HUM_QualCheck == True:

        # Get WC measures during 5 minutes :

        dataFile = None

        # pre allocation
        Last_WC_HUM4 = range(0, N)
        Last_WC_HUM5 = range(0, N)
        Last_WC_HUM6 = range(0, N)

        # reading HUM values during 5 minutes for all 3 HUM sensors
        for i in range(0, N):
            # HUM4
            try:  # urlopen not usable with "with"
                url = "http://" + host + "/api/get/%21s_HUM4"

                # get datapoint for HUM sensor
                dataFile = urllib.urlopen(url, None, 20)

                # store it
                data = dataFile.read(80000)

                Last_WC_HUM4[i] = data

            except:
                print(u"URL=" + (url if url else "") + \
                  u", Message=" + traceback.format_exc())

            # HUM5
            try:  # urlopen not usable with "with"
                url = "http://" + host + "/api/get/%21s_HUM5"

                # get datapoint for HUM sensor
                dataFile = urllib.urlopen(url, None, 20)

                # store it
                Last_WC_HUM5[i] = dataFile.read(80000)

            except:
                print(u"URL=" + (url if url else "") + \
                      u", Message=" + traceback.format_exc())

            # HUM6
            try:  # urlopen not usable with "with"
                url = "http://" + host + "/api/get/%21s_HUM6"

                # get datapoint for HUM sensor
                dataFile = urllib.urlopen(url, None, 20)

                # store it
                Last_WC_HUM6[i] = dataFile.read(80000)

            except:
                print(u"URL=" + (url if url else "") + \
                      u", Message=" + traceback.format_exc())


             # sleep for 1 minutes (until next measure is recored)
            time.sleep(60)

        # Mean WC over 5 minutes
        somme = 0
        for i in range(1, N):
            WC = Last_WC_HUM4[i] # ça c'est juste le petit chippotage pour passer la valeur en '"str"' dans 'float'
            somme = somme + float(WC[1:len(WC) - 1])
        Last_WC_HUM4_mean = somme / N

        somme = 0
        for i in range(1, N):
            WC = Last_WC_HUM5[i]
            somme = somme + float(WC[1:len(WC) - 1])
        Last_WC_HUM5_mean = somme / N

        somme = 0
        for i in range(1, N):
            WC = Last_WC_HUM6[i]
            somme = somme + float(WC[1:len(WC) - 1])
        Last_WC_HUM6_mean = somme / N

        # Mean values of the 3 sensors
        Last_WC_mean = (Last_WC_HUM4_mean + Last_WC_HUM5_mean + Last_WC_HUM6_mean)/3

        # TODO : quality check of datapoints of the post irrigation procedure

        Pot_volume = 12.6  # [L]

        # Determine if additional watering is needed
        if Last_WC_mean < Water_Content_Limit :

            print('Water content after first watering is too low, extra watering is needed')

            # Calculation of additional watering needed
            Dosis = (Water_Content_Limit * Pot_volume - Last_WC_mean * Pot_volume)

            # Calculation of irrigation time
            t = Dosis / Q

            # make irrigation happen
            timestamp = get_timestamp()
            # erase the current file and open the valve in 30 seconds
            open("valve.txt", 'w').write(str(timestamp + 30) + ";1\n")
            # append to the file and close the valve X minute later
            # TODO : set default irrigation time
            open("valve.txt", 'a').write(str(timestamp + 30 + t) + ";0\n")
            print("Extra watering has been processed")
        else :
            print('Water content after first watering is sufficient, no extra watering is needed')



    ## DEFAULT IRRIGATION if WC probes and weather station are down

    if HUM_QualCheck == False and WS_QualCheck == False:
        print('Both water content probes and weather station are down.')
        timestamp = get_timestamp()
        # erase the current file and open the valve in 30 seconds
        open("valve.txt", 'w').write(str(timestamp + 30) + ";1\n")
        # append to the file and close the valve X minute later
        # TODO : set default irrigation time :
        t = 60*30
        open("valve.txt", 'a').write(str(timestamp + t +30) + ";0\n")
        print("A security watering has been processed")

    # TODO : sleep until next day instead of ...
    # sleep for 5 minutes (in seconds)
    time.sleep(5 * 60)

## QUALITY CHECK

# X le numéro du capteur

