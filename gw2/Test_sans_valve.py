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

# Your program must create a data file with one column with the Linux EPOCH time and your valve state (0=closed, 1=opened)
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
              'targets': [{'target': 'HUM3'}, {'target': 'HUM4'}, {'target': 'HUM5'}]}
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
# calcul test pour trouver la valeur moyenne de HUM3 dans la dernière heure
som = 0
length_result = len(result[0].get('datapoints'))
for i in range(0,length_result):
    som = som + result[0].get('datapoints')[i][0]
average = som/length_result = len(result[0].get('datapoints'))
print average

timestamp = get_timestamp()
# erase the current file and open the valve in 30 seconds
open("valve.txt", 'w').write(str(timestamp + 30) + ";1\n")
# append to the file and close the valve 1 minute later
open("valve.txt", 'a').write(str(timestamp + 90) + ";0\n")
print("valve.txt ready.")
# sleep for 5 minutes (in seconds)
time.sleep(5 * 60)

