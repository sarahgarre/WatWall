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
else:
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

# Your program must create a data file with one column with the Linux EPOCH time and your valve state
# (0=closed, 1=opened)
while (True):

    # Example reading last sensor value
    #dataFile = None
    #try:  # urlopen not usable with "with"
    #    url = "http://" + host + "/api/get/%21s_HUM1"
    #    dataFile = urllib.urlopen(url, None, 20)
    #    data = dataFile.read(80000)
    #    print("HUM1=" + data.strip(delimiters))
    #except:
    #    print(u"URL=" + (url if url else "") + \
    #          u", Message=" + traceback.format_exc())
    #if dataFile:
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
    # print VWC

    ## QUALIY CHECK

    # 1/ Set number of successive values to consider
    # TODO : set number of successive data points to consider
    N = 5

    # 2/ Set admissible std (INSERT TRUE VALUE)
    # TODO : set admissible std for each sensor

    LIM_HUM4 = 1
    LIM_HUM5 = 1
    LIM_HUM6 = 1
    LIM_Rn =   1
    LIM_Thr =  1
    LIM_u2 =   1
    LIM_P =    1

    # 3/ computation of std for water content probes

    length_result = len(result[0].get('datapoints'))
    for i in range(length_result - N, length_result):       # pour les N dernières mesures de la journée
        SCE_HUM4 = (result[0].get('datapoints')[i][0] - averageHUM4) ^ 2  # calcul de la somme des carrés des écarts pour HUM4
        SCE_HUM5 = (result[1].get('datapoints')[i][0] - averageHUM5) ^ 2  # calcul de la somme des carrés des écarts pour HUM5
        SCE_HUM6 = (result[2].get('datapoints')[i][0] - averageHUM6) ^ 2  # calcul de la somme des carrés des écarts pour HUM6
    std_HUM4 = math.sqrt((1 / N) * SCE_HUM4)  # calcul du std (écart type)
    std_HUM5 = math.sqrt((1 / N) * SCE_HUM5)   # calcul du std (écart type)
    std_HUM6 = math.sqrt((1 / N) * SCE_HUM6)   # calcul du std (écart type)

    # 4/ computation of std for weather station data

    # pre allocations
    length_result = len(result[0].get('datapoints'))
    sum_Rn =  0
    sum_Thr = 0
    sum_u2 =  0
    sum_P =   0

    # Compute sum & mean
    for i in range(length_result - N, length_result):           # pour les N dernières mesures de la journée
        sum_Rn =   sum_Rn  + result[3].get('datapoints')[i][0]  # sum of data points
        sum_Thr =  sum_Thr + result[6].get('datapoints')[i][0]
        sum_u2 =   sum_u2  + result[5].get('datapoints')[i][0]
        sum_P =    sum_P   + result[8].get('datapoints')[i][0]
    mean_Rn =  sum_Rn  / N
    mean_Thr = sum_Thr / N
    mean_u2 =  sum_u2  / N
    mean_P =   sum_P   / N


    for i in range(length_result - N, length_result):       # pour les N dernières mesures de la journée
        SCE_Rn =  (result[3].get('datapoints')[i][0] - mean_Rn) ^ 2   # calcul de la somme des carrés des écarts
        SCE_Thr = (result[6].get('datapoints')[i][0] - mean_Thr) ^ 2
        SCE_u2 =  (result[5].get('datapoints')[i][0] - mean_u2) ^ 2
        SCE_P =   (result[8].get('datapoints')[i][0] - mean_P) ^ 2
    std_Rn =  math.sqrt((1 / N) * SCE_Rn )  # calcul du std (écart type)
    std_Thr = math.sqrt((1 / N) * SCE_Thr )
    std_u2 =  math.sqrt((1 / N) * SCE_u2 )
    std_P =   math.sqrt((1 / N) * SCE_P )

    ## IRRIGATION DECISION

    # 1/ Set minimum water content
    # TODO : set minimun water content bellow which irrig is triggerd

    Water_Content_Limit_To_Set = 1

    # 2/  Quality check for all 3 WC sensor
    if std_HUM4 < LIM_HUM4 and std_HUM5 < LIM_HUM5 and std_HUM6 < LIM_HUM6 :
        HUM_QualCheck = True
    else :
        HUM_QualCheck = False


    # 3/ Quality check for weather station data
    if std_Rn < LIM_Rn and std_Thr < LIM_Thr and std_u2 < LIM_u2 and std_P < LIM_P :
        WS_QualCheck = True
    else :
        WS_QualCheck = False

    # Check whether irrigation is needed
    if VWC < Water_Content_Limit_To_Set :
        Irrig_Needed = True
    else :
        Irrig_Needed = False


    # IRRIGATION BASED ON WS STARTS :
    # Ici on effectue le calcul d'ET0 pour chaque heure durant les dernières 24h

    if HUM_QualCheck == True and Irrig_Needed == True and WS_QualCheck == True :

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
            for i in range(length_result-(60*24)+(j*60)+1, length_result-((23-j)*60)):
                somme = somme+ result[3].get('datapoints')[i][0]*60/(10**6)
            SommeRn[j] = somme

            # calcul de la température moyenne pour chaque heure -> Thr [°C]
            somme = 0
            length_result = len(result[6].get('datapoints'))
            for i in range(length_result-(60*24)+(j*60)+1, length_result-((23-j)*60)):
                somme = somme + result[6].get('datapoints')[i][0]
            Thr[j] = somme / 60

            # calcul de la pression de vapeur saturante pour chaque heure par l'équation August-Roche-Magnus -> eThr [kPa]
            # (https://en.wikipedia.org/wiki/Vapour_pressure_of_water)
            eThr[j] = 0.61094 * math.exp(17.625 * Thr[j] / (Thr[j] + 243.04))

            # calcul de la pression de vapeur réele -> ea [kPa]
            somme = 0
            length_result = len(result[7].get('datapoints'))
            for i in range(length_result-(60*24)+(j*60)+1, length_result-((23-j)*60)):
                somme = somme + result[7].get('datapoints')[i][0]
            ea[j] = somme / 60

            # calcul de la vitesse moyenne du vent pour chaque heure -> u2 [m/s]
            somme = 0
            length_result = len(result[5].get('datapoints'))
            for i in range(length_result - (60 * 24) + (j * 60)+1, length_result - ((23 - j) * 60)):
                somme = somme + result[5].get('datapoints')[i][0]
            u2[j] = somme / 60
            # u2 = 0.01

            # calcul de la pente de la courbe de pression de vapeur à saturation -> delta [kPa /°C]
            delta[j] = 1635631.478 * math.exp(3525 * Thr[j] / (200 * Thr[j] + 48608)) / (25 * Thr[j] + 6076) ** 2

            # calcul de la pression atmosphérique moyenne pour chaque heure -> P [kPa]
            somme = 0
            length_result = len(result[8].get('datapoints'))
            for i in range(length_result - (60 * 24) + (j * 60)+1, length_result - ((23 - j) * 60) ):
                somme = somme + result[8].get('datapoints')[i][0]
            P[j] = somme/60

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
            for i in range(length_result - (60 * 24) + (j * 60)+1, length_result - ((23 - j) * 60) ):
                Pluvio = somme + result[4].get('datapoints')[i][0] / 60  # on divise par 60 car on cumule des intensités de pluie
                Pluie[j] = Pluvio * Area  # exprimées en mm/h


        print "Yesterday it rained",round(sum(Pluie),3),"litres on our pot."
        print "The ET0 for yesterday was",round(sum(ET0), 3), "mm."

        # Calcul de dose à appliquer pour chaque heure [L]
        Dosis = sum(ET0) * Kl * Area - sum(Pluie)
        if Dosis < 0:
            Dosis = 0
        else:
            Dosis = Dosis
        print "The dosis of water to apply today is ",round(Dosis, 3), "L."

        # calcul du temps d'ouverture de la valve -> t [min]
        Q = 1.5 / 60  # L/min
        t = Dosis / Q
        print "Today we need to open the valve for", round(t, 2), " minutes."

        timestamp = get_timestamp()
        # erase the current file and open the valve in 30 seconds
        open("valve.txt", 'w').write(str(timestamp + 30) + ";1\n")
        # append to the file and close the valve 1 minute later
        open("valve.txt", 'a').write(str(timestamp + 90) + ";0\n")
        print("valve.txt ready.")

        # sleep for irrigation time PLUS x hours
        time.sleep( t + 60*2)

    ## Post-irrigation check

    if HUM_QualCheck == True :

        # TODO :  Somehow get last 5 measures of WC

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

        # TODO :
        #  quality check of data points
        #  set limit value over which 2nd irrigation is completed
        #  compare avg  with limit value
            # if above -> do nothing
            # if bellow -> compute extra water volume

    ## DEFAULT IRRIGATION if WC probes and weather station are down

    if HUM_QualCheck == False and WS_QualCheck == False :

        timestamp = get_timestamp()
        # erase the current file and open the valve in 30 seconds
        open("valve.txt", 'w').write(str(timestamp + 30) + ";1\n")
        # append to the file and close the valve X minute later
        # TODO : set default irrigation time
        open("valve.txt", 'a').write(str(timestamp + 90) + ";0\n")
        print("valve.txt ready.")




    # TODO : sleep until next day instead
    # sleep for 5 minutes (in seconds)
    time.sleep(5 * 60)

## QUALITY CHECK

# X le numéro du capteur
# N le nombre de mesures successives prines en compte

    somme = 0
    length_result = len(result[X].get('datapoints'))
    for i in range(length_result - 5, length_result):       # pour les 5 dernières mesures de la journée
        somme = somme + result[X].get('datapoints')[i][0]   # somme
    MeanX = somme / N                                       # moyenne


    for i in range(length_result - 5, length_result):         # pour les 5 dernières mesures de la journée
        SCE = (result[6].get('datapoints')[i][0] - MeanX)^2   # calcul de la somme des carrés des écarts
    stdX =  sqrt((1/N)*Disp)                                  # calcul du std (écart type)

    if stdX < LIMIT


