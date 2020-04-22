#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from datetime import datetime,date
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

# Your program must create a data file with one column with the Linux EPOCH time and your valve state (0=closed, 1=opened)
while (True):

    # Receuil des données météo de l'heure précédente et nécessaires au calcul de l'ETP
    dataFile = None
    meteo = [[] for i in range(6)]
    j = 0
    try:  # urlopen not usable with "with"
        url = "http://" + host + "/api/grafana/query"
        now = get_timestamp()
        gr = {'range': {'from': formatDateGMT(now - (1 * 60 * 60)), 'to': formatDateGMT(now)}, \
              'targets': [{'target': 'SDI0'}, {'target': 'SDI4'}, {'target': 'SDI7'}, {'target': 'SDI8'},
                          {'target': 'SDI9'}, {'target': 'SDI10'}, ]}
        data = json.dumps(gr)
        dataFile = urllib.urlopen(url, data, 20)
        result = json.load(dataFile)
        if result:
            for target in result:
                index = target.get('target')
                for datapoint in target.get('datapoints'):
                    value = datapoint[0]
                    stamp = datapoint[1] / 1000
                    meteo[j].append(float(value))
                j += 1
    except:
        print(u"URL=" + (url if url else "") + \
              u", Message=" + traceback.format_exc())
    if dataFile:
        dataFile.close()

    # Calcul de l'ETP de l'heure précédente
    ET0 = 0
    Kc = 0.7
    v = []
    for i in range(0, len(meteo)):
        v.append(len(meteo[i]))
    for q in range(0, min(v)):
        delta = (4098 * (0.6108 * math.exp((17.27 * meteo[2][q]) / (meteo[2][q] + 237.3)))) / (
                    (meteo[2][q] + 237.3) ** 2)
        es = 100 * meteo[3][q] / meteo[5][q]
        ea = meteo[3][q]
        altitude = 106  # pour Mont-Saint-Guilbert
        albedo = 0.2
        Rs = meteo[0][q] * 10 ** (-6) * 60
        Rns = (1 - albedo) * Rs
        lat = 50
        sigma = 4.903 * 10 ** (-9) / (24 * 60)
        J = (date.today()-date(2020,1,1)).days+1
        dr = 1 + 0.033 * math.cos((6.28 / 365) * J)
        declinaison = 0.409 * math.sin((6.28 / 365) * J - 1.39)
        ws = math.acos(-math.tan(lat) * math.tan(declinaison))
        Ra = (60 / 3.14) * 0.082 * dr * (
                    ws * math.sin(lat) * math.sin(declinaison) + math.sin(ws) * math.cos(lat) * math.cos(
                declinaison))
        Rso = (0.75 + 210 ** (-5) * altitude) * Ra
        Rnl = sigma * (meteo[2][q] + 273.15) * (0.34 * 0.14 * ea ** 0.5) * (
                    1.35 * (Rs / Rso) - 0.35)
        Rn = Rns - Rnl
        gamma = 0.665 * meteo[4][q] * 10 ** (-3)
        vitesse_du_vent = meteo[1][q]
        # essayons deja sans prendre les longwave
        ET0 += (0.408 * delta * Rn + gamma * (0.625 / (273 + meteo[2][q])) * vitesse_du_vent * (es - ea)) / (
                    delta + gamma * (1 + 0.34 * vitesse_du_vent))
    ETR = ET0 * Kc
    print("L'ETR est de" + " " + str(ETR)+ " "+"mm")

    # Recueil des dernières valeurs d'humidité
    dataFile = None
    humidite = []
    for g in range(1, 4):
        try:  # urlopen not usable with "with"
            url = "http://" + host + "/api/get/%21s_HUM" + unicode(g)
            dataFile = urllib.urlopen(url, None, 20)
            data = dataFile.read(80000)
            humidite.append(float(data.strip(delimiters)))
        except:
            print(u"URL=" + (url if url else "") + \
                  u", Message=" + traceback.format_exc())
        if dataFile:
            dataFile.close()
    print("Les dernières valeurs d'humidité sont respectivement de" + " " + str(
        humidite[0]) + " pour le 1er capteur," + " " + str(humidite[1]) + "" + " pour le second" + " et de" + " " + str(
        humidite[2]) + " pour le dernier")

    # Vérification des données d'humidité
    humidite.sort()

    if humidite[1]-humidite[0]>0.08:
        del humidite[0]
    elif humidite[2]-humidite[1]>0.08:
        del humidite[2]

    # Volume à irriguer
    limite1 = 19.33
    limite2 = 15
    volume_total = "à calculer"
    superficie_au_sol= "à calculer"

    if 100*humidite > limite1:
        V_irrigation = ETR*10**(-2)*superficie_au_sol
    else:
        if 100*humidite < limite2:
            V_irrigation = (limite1-100*min(humidite))*volume_total
        else:
            V_irrigation = (28-100*min(humidite))*volume_total

    # Planning d'irrigation
    temps_irrigation = V_irrigation/1.5
    if temps_irrigation > 1200:
        temps_irrigation = 1200

    timestamp = get_timestamp()
    open("valve.txt", 'a').write(str(timestamp) + ";1\n")
    open("valve.txt", 'a').write(str(timestamp + temps_irrigation) + ";0\n")
    time.sleep(60 * 60)

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
              'targets': [{'target': 'HUM1'}, {'target': 'HUM2'}, {'target': 'HUM3'}]}
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

    timestamp = get_timestamp()
    # erase the current file and open the valve in 30 seconds
    open("valve.txt", 'w').write(str(timestamp + 30) + ";1\n")
    # append to the file and close the valve 1 minute later
    open("valve.txt", 'a').write(str(timestamp + 90) + ";0\n")
    print("valve.txt ready.")
    # sleep for 5 minutes (in seconds)
    time.sleep(5 * 60)

