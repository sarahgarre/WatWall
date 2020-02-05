import socket
import os
import time
import math
import traceback
import urllib2

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

# Your program must create a data file with one column with the Linux EPOCH time and your valve state (0=closed, 1=opened)
while (True):
     try:  # urlopen not usable with "with"
         url = "http://localhost/api/get/%21s_HUM1"
         dataFile = urllib2.urlopen(url, None, 20)
         data = dataFile.read(80000)
         print ("HUM1="+data)
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
     #sleep for 5 minutes (in seconds)
     time.sleep(5*60)
