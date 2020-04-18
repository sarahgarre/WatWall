import os # operating system
import csv # module for csv files
import time

# Parameters
A=1920           # box area [cm2]
Q=1000           # discharge [cm3/hr]
Kc=1             # cultural coefficient [-]


print(os.getcwd())                                          # c=current, w=working, d=directory
os.chdir("C:\Users\pbray\PycharmProjects\WatWall2\gw3")     # from root

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
    time_irrig=ET*A/Q*60*60                                 # Daily watering time based on ET [sec]

    # open the valve the next day (+ 24*60*60) at 00:00
    outfile.write(str(epoch + 24*60*60) + ";1\n")
    # append to the file and close the valve the next day (+ 24*60*60) at 00:00 + time_irrig
    outfile.write(str(epoch + 24*60*60 + time_irrig) + ";0\n")

outfile.close()                                             # close valve.txt
print("valve.txt ready.")
file.close()                                                # close the file






