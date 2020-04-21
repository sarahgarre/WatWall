import csv # module for csv files
import time
import os,sys
import socket


# Parameters
A=1920           # box area [cm2]
Q=1000           # discharge [cm3/hr]
Kc=1             # cultural coefficient [-]

user = "GW3"
test = False
# True to run the code locally
# False to implement the code on the server

# 1) Ensure to run in the user home directory
# !!! MUST NOT BE CHANGED !!!

if test:
    host = "greenwall.gembloux.uliege.be"
else:
    host = "localhost"
    # Ensure to run in the user home directory
    DIR_BASE = os.path.expanduser("~")
    if not os.path.samefile(os.getcwd(), DIR_BASE):
        os.chdir(DIR_BASE)
    print(os.getcwd())

# 2)Ensure to be the only instance to run
# !!! MUST NOT BE CHANGED !!!
# Explanation: if another program is running, it gets killed and replaced by this one

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


# ET file of Gembloux
file=open("ET0_2010_2019.csv","r")                          # open the file
reader = csv.reader(file, delimiter = ";")                  # file reading initialization

next(reader)
next(reader)

outfile = open('valve.txt','w')

for row in reader:                                          # loop to go through the reader
    print (row[0])                                          # display rows

    # Convert datetime into epoch
    hiredate = row[0]                                       # select date in the list
    pattern = '%d/%m/%Y %H:%M'                              # date format
    epoch = int(time.mktime(time.strptime(hiredate, pattern)))  # convert date to epoch time
    print epoch

    # Calculate irrigation time
    ET0=float(row[1])                                       # Daily reference evapotranspiration [mm/day]
    ET=Kc*ET0/10                                            # Daily evapotranspiration [cm/day]
    time_irrig=int(ET*A/Q*60*60)                            # Daily watering time based on ET [sec]

    # open the valve the next day (+ 24*60*60) at 00:00
    outfile.write(str(epoch + 24*60*60) + ";1\n")
    # append to the file and close the valve the next day (+ 24*60*60) at 00:00 + time_irrig
    outfile.write(str(epoch + 24*60*60 + time_irrig) + ";0\n")

outfile.close()                                             # close valve.txt
print("valve.txt ready.")
file.close()                                                # close the file






