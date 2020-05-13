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
import matplotlib.pyplot as plt
import numpy as np

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

# Collecte des données d'humidité et de pluie sur le dernier mois

dataFile = None
Emplacement=['HUM1.csv','HUM2.csv','HUM3.csv','Pluie.csv'] # donne dans quel fichier csv les données doivent être ajoutées
p=0 # Compteur qui permet de passer au fichier csv suivant
for k in range(0,4): # initialise les fichiers csv comme étant initialement vides
    open("Graphiques/"+Emplacement[k],'w').write("")
try:  # urlopen not usable with "with"
    url = "http://" + host + "/api/grafana/query"
    now = get_timestamp()
    gr = {'range': {'from': formatDateGMT(now - (30 * 24 * 60 * 60)), 'to': formatDateGMT(now)}, \
          'targets': [{'target': 'HUM1'}, {'target': 'HUM2'}, {'target': 'HUM3'}, {'target': 'SDI1'}]}
    data = json.dumps(gr)
    dataFile = urllib.urlopen(url, data, 20)
    result = json.load(dataFile)
    if result:
        for target in result:
            index = target.get('target')
            for datapoint in target.get('datapoints'):
                value = datapoint[0]
                stamp = datapoint[1] / 1000
                if p==3:
                    open("Graphiques/"+Emplacement[p],'a').write(str(value)+"\n") # note juste la valeur si c'est pas pour l'humidité
                else:
                    open("Graphiques/" + Emplacement[p], 'a').write(str(round((35.24*value-15.44)/(value-0.3747),4)) + "\n") # en plus fait la conversion en humidité
            p+=1
except:
    print(u"URL=" + (url if url else "") + \
          u", Message=" + traceback.format_exc())
if dataFile:
    dataFile.close()

# Tracé des courbes d'humidité et de pluviométrie

debut_abscisse= (datetime.datetime.now()+datetime.timedelta(-30)) # trouve la date 30 jours plus tôt
fin_abscisse=datetime.datetime.now() # trouve la date du jour

# Nous gardons uniquement la date, pas l'heure qui nous est inutile dans le graph
debut_abscisse=debut_abscisse.date()
fin_abscisse=fin_abscisse.date()

X=np.linspace(debut_abscisse,fin_abscisse, 5)




