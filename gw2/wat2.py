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

    # vérification de la qualité de la mesure




    #Ici on effectue le calcul d'ET0 pour chaque heure durant les dernières 24h
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

        # Crop coefficient [Temporaire] #TODO
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



    # if par rapport à la valeur d'humidité

    timestamp = get_timestamp()
    # erase the current file and open the valve in 30 seconds
    open("valve.txt", 'w').write(str(timestamp + 30) + ";1\n")
    # append to the file and close the valve 1 minute later
    open("valve.txt", 'a').write(str(timestamp + 90) + ";0\n")
    print("valve.txt ready.")
    # sleep for 5 minutes (in seconds)
    time.sleep(5 * 60)
