# First import the necessary modules
import scipy as sp
import numpy as np
# Visualization libraries
import matplotlib.pyplot as plt
import seaborn as sb
# Data analysis library
import pandas as pd
# WOrking with dates
import datetime
import sys
import os

datadir='sample_data'
os.chdir(datadir)
# Import data files downloaded manually from Grafana and placed in the same folder as this notebook
HUM1 = pd.read_csv("s_2.csv",sep='\t', header=None, decimal=",") # Take care, the CSV file uses , as decimal. Python uses . If we don't indicate this, it will not recognize the sensor signal as a number.
HUM1.columns = ['Time','Volt']
HUM2 = pd.read_csv("s_12.csv",sep='\t', header=None, decimal=",")
HUM2.columns = ['Time','Volt']
HUM3 = pd.read_csv("s_15.csv",sep='\t', header=None, decimal=",")
HUM3.columns = ['Time','Volt']
RAIN = pd.read_csv("s_18.csv",sep='\t', header=None, decimal=",")
RAIN.columns = ['Time','R_mm']
os.chdir('..')

## Convert time string to a number
t_stamp1= pd.to_datetime(HUM1['Time'])
t_stamp2= pd.to_datetime(HUM2['Time'])
t_stamp3= pd.to_datetime(HUM3['Time'])
RAIN['tstamp']= pd.to_datetime(RAIN['Time'])

## If you want to use epoch time:
# To get the epoch from a datetime object, you can convert the series to an int64 object.
# This will give you the number of nanoseconds since the epoch,
# and divide by 10^9 (the number of nanoseconds in a second).
# The last conversion is necessary if you want integer as a result and not a float.
t_epoch1 = (t_stamp1.values.astype(np.int64)/10**9).astype(np.int64)
t_epoch2 = (t_stamp2.values.astype(np.int64)/10**9).astype(np.int64)
t_epoch3 = (t_stamp3.values.astype(np.int64)/10**9).astype(np.int64)

# trim the timestamps to get the datetime object
dates = RAIN['tstamp'].dt.floor('D')
#aggregate size if want count NaNs
#aggregate count if want omit NaNs
df = RAIN.groupby(dates).size()
print (df)

#if need sums
dailyR= RAIN.groupby(dates)['R_mm'].sum().reset_index()

# Construct a new dataframe containing all soil moisture data
data = {'Time': t_stamp1,'Raw1_V': HUM1['Volt']}
HUM = pd.DataFrame(data, columns = ['Time', 'Raw1_V'])

# Interpolate all soil moisture data on the same time vector (not necessary for plotting, but for certain calculations)
HUM['Raw2_V'] = np.interp(t_stamp1, t_stamp2, HUM2['Volt'])
HUM['Raw3_V'] = np.interp(t_stamp1, t_stamp3, HUM3['Volt'])

dstart = dstart = datetime.datetime(2020,4,1)
datenow = datetime.datetime.now()

fig1 = plt.figure(figsize=(20,15))
ax1 = plt.subplot(211)
out0 = ax1.bar(dailyR['tstamp'],dailyR['R_mm'],color='b')
plt.gca().invert_yaxis() #invert secondary y-axis to have bars coming from the top of the plot
plt.xlim(dstart, datenow)
ax1.set_xlabel("Date")
ax1.set_ylabel("R [mm/d]")
ax1.grid()

ax2 = plt.subplot(212)
out1= plt.plot_date(HUM['Time'],HUM['Raw1_V'],'-',xdate=True)
out2= plt.plot_date(HUM['Time'],HUM['Raw2_V'],'-',xdate=True)
out3= plt.plot_date(HUM['Time'],HUM['Raw3_V'],'-',xdate=True)
ax2.set_xlabel("Date")
ax2.set_ylabel("Voltage [V]")
plt.xlim(dstart, datenow)
ax2.set_ylim([0.35, 0.65])
ax2.grid()
plt.legend(['HUM1','HUM2','HUM3'])