import os # operating system
import csv # module for csv files

print(os.getcwd())  # c=current, w=working, d=directory
os.chdir("C:\Users\pbray\PycharmProjects\WatWall\gw3")    #from root

# ET file of Gembloux
file=open("ET0_2010_2019.csv","r")  # open the file
reader = csv.reader(file, delimiter = ";")  # file reading initialization
for row in reader:  # loop to go through the reader
    print (row)   # display rows
file.close()    # close the file



