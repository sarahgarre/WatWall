#test push
#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from datetime import datetime
import time
import calendar
import json
import math
import os,sys
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
        _lock_socket.bind('\0'+user)
        print('Socket '+user+' now locked for process #' + pid)
        # Make the current pid available to be able to kill the process...
        open("pid.txt", 'w').write(pid)
    except socket.error:
        current = open("pid.txt", 'r').read()
        print(user+' lock exists for process #' + current + " : may be you should ./clean.sh !")
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
    dt = datetime.fromtimestamp(epoch - (2 * 60 * 60) ) # We are in summer and in Belgium !
    return dt.isoformat()

delimiters = ' \t\n\r\"\''

# Getting the list of all available sensors
dataFile = None
try:  # urlopen not usable with "with"
    url = "http://" +host +"/api/grafana/search"
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
    dataFile = None
    try:  # urlopen not usable with "with"
        url = "http://" +host +"/api/get/%21s_HUM1"
        dataFile = urllib.urlopen(url, None, 20)
        data = dataFile.read(80000)
        print("HUM1=" + data.strip(delimiters))
    except:
        print(u"URL=" + (url if url else "") + \
              u", Message=" + traceback.format_exc())
    if dataFile:
        dataFile.close()

    # Example reading all values of the last hour (60 minutes of 60 seconds)
    dataFile = None
    try:  # urlopen not usable with "with"
        url = "http://" +host +"/api/grafana/query"
        now = get_timestamp()
        gr = {'range': {'from': formatDateGMT(now - (1 * 60 * 60)), 'to': formatDateGMT(now)}, \
              'targets': [{'target': 'HUM4'}, {'target': 'HUM5'}, {'target': 'HUM6'}, {'target': 'SDI0'}, {'target': 'SDI1'}, {'target': 'SDI4'}, {'target': 'SDI7'}, {'target': 'SDI8'}, {'target': 'SDI9'}, {'target': 'SDI10'}]}
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

    # calcul de la valeur moyenne de HUM5 dans la dernière heure -> averageHUM4
    somme = 0
    length_result = len(result[0].get('datapoints'))
    for i in range(0, length_result):
        somme = somme + result[0].get('datapoints')[i][0]
    averageHUM4 = somme/length_result
    print averageHUM4

    # calcul de la valeur moyenne de HUM5 dans la dernière heure -> averageHUM5
    somme = 0
    length_result = len(result[1].get('datapoints'))
    for i in range(0, length_result):
        somme = somme + result[1].get('datapoints')[i][0]
    averageHUM5 = somme / length_result
    print averageHUM5

    # calcul de la valeur moyenne de HUM5 dans la dernière heure -> averageHUM6
    somme = 0
    length_result = len(result[2].get('datapoints'))
    for i in range(0, length_result):
        somme = somme + result[2].get('datapoints')[i][0]
    averageHUM6 = somme / length_result
    print averageHUM6

    # calcul de la moyenne des 3 sondes -> averageHUM456
    averageHUM456 = (averageHUM4 + averageHUM5 + averageHUM6)/3
    print averageHUM456

    # calibration
    # vérification de la qualité de la mesure


    # calcul de la somme des radiations pour la dernière heure -> Rn [MJ/(m2 hour)]
    somme = 0
    length_result = len(result[3].get('datapoints'))
    for i in range(0, length_result):
        sommeRn = somme + result[3].get('datapoints')[i][0]
    sommeRn = sommeRn * 0.0036
    print sommeRn

    # calcul de la température moyenne pour la dernière heure -> Thr [°C]
    somme = 0
    length_result = len(result[6].get('datapoints'))
    for i in range(0, length_result):
        somme = somme + result[6].get('datapoints')[i][0]
    Thr = somme / length_result
    print Thr

    # calcul de la pression de vapeur saturante pour la dernière heure par l'équation August-Roche-Magnus -> eThr [kPa]
    # (https://en.wikipedia.org/wiki/Vapour_pressure_of_water)
    eThr = 0.61094*math.exp(17.625*Thr/(Thr + 243.04))
    print eThr

    # calcul de la pression de vapeur réele -> ea [kPa]
    somme = 0
    length_result = len(result[7].get('datapoints'))
    for i in range(0, length_result):
        somme = somme + result[7].get('datapoints')[i][0]
    ea = somme / length_result
    print ea

    # calcul de la vitesse moyenne du vent pour la dernière heure -> u2 [m/s]
    somme = 0
    length_result = len(result[5].get('datapoints'))
    for i in range(0, length_result):
        somme = somme + result[5].get('datapoints')[i][0]
    u2 = somme / length_result
    print u2

    # calcul de la pente de la courbe de pression de vapeur à saturation -> delta [kPa /°C]
    delta = 1635631.478*math.exp(3525*Thr/(200*Thr + 48608))/(25*Thr + 6076)**2
    print delta

    # calcul de la pression atmosphérique moyenne pour la dernière heure -> P [kPa]
    somme = 0
    length_result = len(result[8].get('datapoints'))
    for i in range(0, length_result):
        somme = somme + result[8].get('datapoints')[i][0]
    P = somme / length_result
    print P

    # calcul de la constante psychrométrique -> gamma [kPa/°C] https://en.wikipedia.org/wiki/Psychrometric_constant
    Cp = 0.001005  # Specific Heat Capacities of Air at 300 K [MJ/Kg K]
                   # https://www.ohio.edu/mechanical/thermo/property_tables/air/air_Cp_Cv.html
    lambdav = 2.26  # Latent heat of water vaporization [MJ / kg]
    MW_ratio = 0.622 # Ratio molecular weight of water vapor/dry air
    gamma = Cp*P/(lambdav*MW_ratio)
    print gamma

    # formule ET0 [mm/hour]
    ET0h = (0.408* delta * sommeRn + gamma * 37 / (Thr + 273) * u2 *(eThr-ea))/(delta+gamma*(1 + 0.34 * u2))
    print ET0h

    # formule de Kl

    # Calcul de dose en prenant la pluie en compte

    # if par rapport à la valeur d'humidité


    timestamp = get_timestamp()
    # erase the current file and open the valve in 30 seconds
    open("valve.txt", 'w').write(str(timestamp + 30) + ";1\n")
    # append to the file and close the valve 1 minute later
    open("valve.txt", 'a').write(str(timestamp + 90) + ";0\n")
    print("valve.txt ready.")
    # sleep for 5 minutes (in seconds)
    time.sleep(5 * 60)

