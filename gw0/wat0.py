import socket
import os
import time
import math
import traceback
import urllib2
import json

# Ensure to run in the user home directory
DIR_BASE = os.path.expanduser("~")
if not os.path.samefile(os.getcwd(), DIR_BASE):
     os.chdir(DIR_BASE)
print os.getcwd()

# Ensure to be the only instance to run
pid = str(os.getpid())
_lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)

try:
     _lock_socket.bind('\0GW0')
     print ('Socket GW0 now locked for process #'+pid)
     # Make the current pid available to be able to kill the process...
     file("pid.txt", 'w').write(pid)
except socket.error:
     current = file("pid.txt", 'r').read()
     print ('GW0 lock exists for process #'+current+" : may be you should ./clean.sh !")
     sys.exit()

#EPOCH time is the number of seconds since 1/1/1970
def get_timestamp():
    now = time.time()
    now = math.floor(float(now))
    now = int(now)
    return now

#Transform an EPOCH time in a lisible date (for Grafana)
def formatDate(epoch):
    return time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(epoch))

delimiters = ' \t\n\r\"\''

# Getting the list of all available sensors
dataFile = None
try:  # urlopen not usable with "with"
    url = "http://localhost/api/grafana/search"
    dataFile = urllib2.urlopen(url, json.dumps(""), 20)
    result = json.load(dataFile)
    for index in result:
        print(index)
except:
    print (u"URL=" + (url if url else "") + \
           u", Message=" + traceback.format_exc())
if dataFile:
    dataFile.close()

# Your program must create a data file with one column with the Linux EPOCH time and your valve state (0=closed, 1=opened)
while (True):

     # Example reading last sensor value
     dataFile = None
     try:  # urlopen not usable with "with"
         url = "http://localhost/api/get/%21s_HUM1"
         dataFile = urllib2.urlopen(url, None, 20)
         data = dataFile.read(80000)
         print ("HUM1="+data.strip(delimiters))
     except:
         print (u"URL=" + (url if url else "") + \
                            u", Message=" + traceback.format_exc() )
     if dataFile:
          dataFile.close()

     # Example reading values of the last hour (60 minutes of 60 seconds)
     dataFile = None
     try:  # urlopen not usable with "with"
         url = "http://localhost/api/grafana/query"
         now = get_timestamp()
         gr = { 'range': { 'from': formatDate(now-60*60), 'to': formatDate(now) }, \
                'targets': [{'target':'HUM1'} ,{'target':'HUM2'},{'target':'HUM3'}] }
         data = json.dumps(gr)
         # print data
         dataFile = urllib2.urlopen(url, data, 20)
         result = json.load(dataFile)
         if result:
             print result
             for target in result:
                 # print target
                 index = target.get('target')
                 for datapoint in target.get('datapoints'):
                     value = datapoint[0]
                     stamp = datapoint[1]
                     print (index+": "+formatDate(stamp)+" = "+value)
     except:
         print (u"URL=" + (url if url else "") + \
                            u", Message=" + traceback.format_exc() )
     if dataFile:
          dataFile.close()

     timestamp = get_timestamp()
     #erase the current file and open the valve in 30 seconds
     file("valve.txt", 'w').write(unicode(timestamp+30)+";1\n")
     #append to the file and close the valve 1 minute later
     file("valve.txt", 'a').write(unicode(timestamp+90)+";0\n")
     print ("valve.txt ready.")
     #sleep for 5 minutes (in seconds)
     time.sleep(5*60)
