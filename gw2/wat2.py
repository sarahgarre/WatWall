############################
#    Libraries imports    #
############################

from datetime import datetime
import time
import calendar
import json
import math
import os, sys
import socket
import traceback
import urllib2 as urllib

##############################################################################
#                            Program settings                                #
##############################################################################
# Please enter the hour at which program is launched on the server :
hour = 16
minute = 25
##############################################################################
# Please specify if you are testing the program & if you want to delay run :
test = False
Delay = True
##############################################################################
# Discharge of the porous hose network Q[L/min] :
Q = 1.5 / 60
##############################################################################
# Calibration parameters :
m_calib = 96
p_calib = - 30
##############################################################################
## QUALITY CHECK
# Number of successive values to consider :
N = 5
# Admissible max std for environmental param :
LIM_Rn = 322.5866
LIM_Thr = 2.8370
LIM_u2 = 1.231
LIM_P = 0.0678
# Admissible max std for WC probes  :
LIM_HUM4 = 0.1131
LIM_HUM5 = 0.1340
LIM_HUM6 = 0.1135
#TODO compute std space
LIM_HUM456 = 1
##############################################################################
## IRRIGATION DECISION
# Minimum water content admissible :
Water_Content_Limit = 30
# Crop coefficient
Kl = 0.7
# Waiting time between first irrigation and post-irrig check :
waiting_time = 3600 * 2
# Default irrigation time [seconds] :
default_irrig = 60 * 30
# Dimensions of the pot/module [m2] :
Area = 0.75 * 0.14
# Volume of the pot/module [L] :
Pot_volume = 12.6
##############################################################################

##########################################
#    COMMUNICATION PROTOCOLS settings    #
##########################################

user = "GW2"
if test:
    host = "greenwall.gembloux.uliege.be"
    print('Script running  on ''local'' mode')
else:
    print('Script running on ''network'' mode')
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
        _lock_socket.bind('\0' + user)
        print('Socket ' + user + ' now locked for process #' + pid)
        # Make the current pid available to be able to kill the process...
        open("pid.txt", 'w').write(pid)
    except socket.error:
        current = open("pid.txt", 'r').read()
        print(user + ' lock exists for process #' + current + " : may be you should ./clean.sh !")
        sys.exit()


##################################
#    TIME MANAGEMENT settings    #
##################################

# EPOCH time is the number of seconds since 1/1/1970
def get_timestamp():
    return int(time.time())


# Transform an EPOCH time in a lisible date (for Grafana)
def formatDate(epoch):
    dt = datetime.fromtimestamp(epoch)
    return dt.isoformat()


# Transform an EPOCH time in a lisible date (for Grafana)
def formatDateGMT(epoch):
    dt = datetime.fromtimestamp(epoch - (2 * 60 * 60))  # We are in summer and in Belgium !
    return dt.isoformat()


delimiters = ' \t\n\r\"\''

if Delay:

    # waiting_time is the number of seconds between now and the next 6AM
    start_delay = (24 - hour + 6) * 3600 - (60 * minute) # [seconds]

    timestamp = get_timestamp()

    print 'The script has been loaded successfully at', time.strftime('%I:%M%p', time.localtime(timestamp))
    print 'Irrigation algorithm will start tomorrow at',  time.strftime('%I:%M%p', time.localtime(timestamp+start_delay)), ', within', start_delay / 3600, 'hours'

    # To get messages in nohup.out
    sys.stdout.flush()
    time.sleep(start_delay)
else:
    print 'No delay before starting the scrip has been set'
    print 'The script will start right away'


print ''
print 'Here is the list of all the input setting of the script :'
print '========================================================='
print ''
print '* The discharge of the drip pipe :', round(Q, 2), 'L/min'
print '* The number of successive measures used for data quality check :', int(N)
print '* The minimum admissible water content :', int(Water_Content_Limit), '%'
print '* The landscape coefficient Kl', round(Kl, 2), '-'
print '* The delay between first irrigation and post irrigation check : ', int(waiting_time/60), 'minutes'
print '* The surface of the module :', round(Area, 2), 'm2'
print '* The volume of the module :', round(Pot_volume, 2), 'L'
print '* The admissible standard deviation for the sensors over time :'
print '    * HUM4   :', round(LIM_HUM4,2)
print '    * HUM5   :', round(LIM_HUM5,2)
print '    * HUM6   :', round(LIM_HUM6,2)
print '    * Rn     :', round(LIM_Rn, 2)
print '    * Thr    :', round(LIM_Thr, 2)
print '    * u2     :', round(LIM_u2, 2)
print '    * P      :', round(LIM_P, 2)
print '* The admissible standard deviation for the sensors over space :'
print '    * HUM456 :', round(LIM_HUM456,2)





################################################################################
#                     *** IRRIGATION DECISION ALGORITHM ***                    #
################################################################################

while (True):

    print ''
    print '==============================================================================='
    print '=         A new day of irrigation management of the WattWall starts           ='
    print '==============================================================================='

    timestamp = get_timestamp()
    print 'Today is', time.strftime('%A %d %B %Y', time.localtime(timestamp))
    print 'It is now', time.strftime('%I:%M%p', time.localtime(timestamp)),', watering of the living wall module will start'

    # Getting tomorrow starting time  (for script shut down period)
    tomorrow = get_timestamp() + 24 * 60 * 60

    #########################
    #    Data collection    #
    #########################

    print('Data from the last 24h is being collected...')
    dataFile = None
    try:  # urlopen not usable with "with"
        url = "http://" + host + "/api/grafana/query"
        now = get_timestamp()
        gr = {'range': {'from': formatDateGMT(now - (24 * 60 * 60)), 'to': formatDateGMT(now)}, \
              'targets': [{'target': 'HUM4'}, {'target': 'HUM5'}, {'target': 'HUM6'}, {'target': 'SDI0'},
                          {'target': 'SDI1'}, {'target': 'SDI4'}, {'target': 'SDI7'}, {'target': 'SDI8'},
                          {'target': 'SDI9'}, {'target': 'SDI10'}]}
        data = json.dumps(gr)
        # print(data)
        dataFile = urllib.urlopen(url, data, 20)
        result = json.load(dataFile)
        if result:
            # print(result)
            for target in result:
                # print target
                index = target.get('target')
                for datapoint in target.get('datapoints'):
                    value = datapoint[0]
                    stamp = datapoint[1] / 1000
                    # print(index + ": " + formatDate(stamp) + " = " + str(value))
    except:
        print(u"URL=" + (url if url else "") + \
              u", Message=" + traceback.format_exc())
    if dataFile:
        dataFile.close()


    # TODO mean WC over 24h or 5 min ??
    # indeed at 24h, to be changed
    # mean HUM value calculation

    somme = 0
    length_result = len(result[0].get('datapoints'))
    for i in range(length_result-N, length_result):
        somme = somme + result[0].get('datapoints')[i][0]
    averageHUM4 = somme / N

    somme = 0
    length_result = len(result[1].get('datapoints'))
    for i in range(length_result-N, length_result):
        somme = somme + result[1].get('datapoints')[i][0]
    averageHUM5 = somme / N
    somme = 0
    length_result = len(result[2].get('datapoints'))
    for i in range(length_result-5, length_result):
        somme = somme + result[2].get('datapoints')[i][0]
    averageHUM6 = somme / N

    # Mean water content value - averageHUM456
    averageHUM456 = (averageHUM4 + averageHUM5 + averageHUM6) / 3

    # TODO here thze std is over the full day ...
    # std deviation between sensors
    # sqrt( (1/N-1) * sum(measure - mean)^2 )
    std_HUM456 = math.sqrt((1/float(2))*(pow((averageHUM4 - averageHUM456), 2) + pow((averageHUM5 - averageHUM456), 2) + pow((averageHUM6 - averageHUM456), 2)))

    VWC = m_calib * averageHUM456 + p_calib

    ###########################
    #    Data QUALIY CHECK    #
    ###########################
    print 'Reliability of the collected data will determined'

    # 3/ computation of std for water content probes

    # pre allocation
    SCE_HUM4 = 0
    SCE_HUM5 = 0
    SCE_HUM6 = 0

    # mean squared error and std calculation
    length_result = len(result[0].get('datapoints'))
    # for the last N measures of the day
    for i in range(length_result - N, length_result):
        # calculation of the sum of deviations
        SCE_HUM4 = SCE_HUM4 + pow((result[0].get('datapoints')[i][0] - averageHUM4), 2)
    # computation of  std
    # sqrt( (1/N-1) * sum(measure - mean)^2 )
    std_HUM4 = math.sqrt((1/float(N-1))  * SCE_HUM4)


    # mean squared error and std calculation
    length_result = len(result[1].get('datapoints'))
    # for the last N measures of the day
    for i in range(length_result - N, length_result):
        # calculation of the sum of deviations
        SCE_HUM5 = SCE_HUM5 + pow((result[1].get('datapoints')[i][0] - averageHUM5), 2)
    # computation of  std
    # sqrt( (1/N-1) * sum(measure - mean)^2 )
    std_HUM5 = math.sqrt((1/float(N-1))  * SCE_HUM5)


    # mean squared error and std calculation
    length_result = len(result[0].get('datapoints'))
    # for the last N measures of the day
    for i in range(length_result - N, length_result):
        # calculation of the sum of deviations
        SCE_HUM6 = SCE_HUM6 + pow((result[2].get('datapoints')[i][0] - averageHUM6), 2)
    # computation of  std
    # sqrt( (1/N-1) * sum(measure - mean)^2 )
    std_HUM6 = math.sqrt((1/float(N-1))  * SCE_HUM6)

    # 4/ computation of std for weather station data

    # pre allocations
    sum_Rn = 0
    sum_Thr = 0
    sum_u2 = 0
    sum_P = 0

    # Compute sum & mean
    length_result = len(result[3].get('datapoints'))
    for i in range(length_result - N, length_result):  # for the last N measures of the day
        sum_Rn = sum_Rn + result[3].get('datapoints')[i][0]  # sum of data points
    mean_Rn = sum_Rn / N  # mean of datapoints

    # Compute sum & mean for pressure
    length_result = len(result[6].get('datapoints'))
    for i in range(length_result - N, length_result):  # for the last N measures of the day
        sum_Thr = sum_Thr + result[6].get('datapoints')[i][0]
    # mean of datapoints
    mean_Thr = sum_Thr / N

    # Compute sum & mean for pressure
    length_result = len(result[5].get('datapoints'))
    for i in range(length_result - N, length_result):  # for the last N measures of the day
        sum_u2 = sum_u2 + result[5].get('datapoints')[i][0]
    # mean of datapoints
    mean_u2 = sum_u2 / N

    # Compute sum & mean for pressure
    length_result = len(result[8].get('datapoints'))
    for i in range(length_result - N, length_result):  # for the last N measures of the day
        sum_P = sum_P + result[8].get('datapoints')[i][0]  # sum of data points
    # mean of datapoints
    mean_P = sum_P / N


    # pre allocation
    SCE_Rn = 0
    SCE_Thr = 0
    SCE_u2 = 0
    SCE_P = 0


    # TODO split for loop calculation, unconsistant lenth of vectors
    # mean squared error and std calculation
    # For the last N measures of the day
    length_result = len(result[3].get('datapoints'))
    for i in range(length_result - N, length_result):
        # calculation of the sum of deviations
        SCE_Rn = SCE_Rn + pow((result[3].get('datapoints')[i][0] - mean_Rn), 2)
    # compuation of std
    # sqrt( (1/N-1) * sum(measure - mean)^2 )
    std_Rn =  math.sqrt((1/float(N-1))  * SCE_Rn)


    length_result = len(result[6].get('datapoints'))
    for i in range(length_result - N, length_result):
        # calculation of the sum of deviations
        SCE_Thr = SCE_Thr + pow((result[6].get('datapoints')[i][0] - mean_Thr), 2)
    # compuation of std
    # sqrt( (1/N-1) * sum(measure - mean)^2 )
    std_Thr = math.sqrt((1/float(N-1))  * SCE_Thr)

    length_result = len(result[5].get('datapoints'))
    for i in range(length_result - N, length_result):
        # calculation of the sum of deviations
        SCE_u2 = SCE_u2 + pow((result[5].get('datapoints')[i][0] - mean_u2), 2)
    # compuation of std
    # sqrt( (1/N-1) * sum(measure - mean)^2 )
    std_u2 =  math.sqrt((1/float(N-1))  * SCE_u2)

    length_result = len(result[8].get('datapoints'))
    for i in range(length_result - N, length_result):
        # calculation of the sum of deviations
        SCE_P = SCE_P + pow((result[8].get('datapoints')[i][0] - mean_P), 2)
    # compuation of std
    # sqrt( (1/N-1) * sum(measure - mean)^2 )
    std_P =   math.sqrt((1/float(N-1))  * SCE_P)


    print ""
    print 'Sensors quality check :'
    print '======================='

    print 'Here is the standard deviation over', int(N), 'minutes for the sensors :'

    print '   * HUM4    :  ', round(std_HUM4, 3)
    print '   * HUM5    :  ', round(std_HUM5, 3)
    print '   * HUM6    :  ', round(std_HUM6, 3)
    print '   * Rn      :  ', round(std_Rn, 3)
    print '   * Temp    :  ', round(std_Thr, 3)
    print '   * Wind    :  ', round(std_u2, 3)
    print '   * atmPres :  ', round(std_P, 3)
    print 'Here is the standard deviation over space for HUM sensors :'
    print '   * HUM456  :  ', round(std_HUM456, 3)

    print''
    print('Quality check result :')

    # 1/  Quality check for all 3 WC sensor
    if std_HUM4 < LIM_HUM4 and std_HUM5 < LIM_HUM5 and std_HUM6 < LIM_HUM6 and std_HUM456 < LIM_HUM456:
        HUM_QualCheck = True
        print('-> Water content probe is working')
    else:
        HUM_QualCheck = False
        print('-> Water content probe is NOT working')

    # 2/ Quality check for weather station data
    if std_Rn < LIM_Rn and std_Thr < LIM_Thr and std_u2 < LIM_u2 and std_P < LIM_P:
        WS_QualCheck = True
        print('-> Weather station is working')
    else:
        WS_QualCheck = False
        print('-> Weather station is NOT working')

    ########################################
    #    CHECK IF FIRST IRRIG IS NEEDED    #
    ########################################

    if VWC < Water_Content_Limit:
        Irrig_Needed = True
    else:
        Irrig_Needed = False

    ################################
    #    IRRIGATION BASED ON WS    #
    ################################

    # 1/ ET0 calculation for the last 24 h :

    # if quality check ok
    if HUM_QualCheck == True and WS_QualCheck == True:

        # pre allocations
        SommeRn = range(23)
        Thr = range(23)
        eThr = range(23)
        ea = range(23)
        u2 = range(23)
        delta = range(23)
        P = range(23)
        gamma = range(23)
        ET0 = range(23)
        Pluie = range(23)

        # for each hour of the day
        for j in range(0, 23):

            # A - Computation of irradiation for each hour - Rn[MJ/(m2 hour)]
            somme = 0
            a = 0
            length_result = len(result[3].get('datapoints'))
            for i in range(length_result - (60 * 24) + (j * 60) + 1, length_result - ((23 - j) * 60)):
                somme = somme + result[3].get('datapoints')[i][0] * 60 / (10 ** 6)
            SommeRn[j] = somme

            # B - computation of mean temprature for each hour - Thr[degree C]
            somme = 0
            length_result = len(result[6].get('datapoints'))
            for i in range(length_result - (60 * 24) + (j * 60) + 1, length_result - ((23 - j) * 60)):
                somme = somme + result[6].get('datapoints')[i][0]
            Thr[j] = somme / 60

            # C - Computation of the vapor pressure for each hour of the day August-Roche-Magnus equation - eThr[kPa]
            # For equation see : https://en.wikipedia.org/wiki/Vapour_pressure_of_water
            eThr[j] = 0.61094 * math.exp(17.625 * Thr[j] / (Thr[j] + 243.04))

            # D - Computation of real vapor pressure - ea[kPa]
            somme = 0
            length_result = len(result[7].get('datapoints'))
            for i in range(length_result - (60 * 24) + (j * 60) + 1, length_result - ((23 - j) * 60)):
                somme = somme + result[7].get('datapoints')[i][0]
            ea[j] = somme / 60

            # E - Computation of mean wind speed for each hour - u2[m/s]
            somme = 0
            length_result = len(result[5].get('datapoints'))
            for i in range(length_result - (60 * 24) + (j * 60) + 1, length_result - ((23 - j) * 60)):
                somme = somme + result[5].get('datapoints')[i][0]
            u2[j] = somme / 60
            # u2 = 0.01

            # F - Computation of the slope of ths saturation vapor pressure curve - delta [kPa /degree C]
            delta[j] = 1635631.478 * math.exp(3525 * Thr[j] / (200 * Thr[j] + 48608)) / (25 * Thr[j] + 6076) ** 2

            # G - Computation of mean atmospheric pressure for each hour - P[kPa]
            somme = 0
            length_result = len(result[8].get('datapoints'))
            for i in range(length_result - (60 * 24) + (j * 60) + 1, length_result - ((23 - j) * 60)):
                somme = somme + result[8].get('datapoints')[i][0]
            P[j] = somme / 60

            # H - Computation of the psychrometric constant - gamma [kPa/ degree C]
            # For additional information see  https://en.wikipedia.org/wiki/Psychrometric_constant

            Cp = 0.001005  # Specific Heat Capacity of Air at 300 K [MJ/Kg K]
            # Source : https://www.ohio.edu/mechanical/thermo/property_tables/air/air_Cp_Cv.html

            lambdav = 2.26  # Latent heat of water vaporization [MJ / kg]
            MW_ratio = 0.622  # Ratio molecular weight of water vapor/dry air

            gamma[j] = Cp * P[j] / (lambdav * MW_ratio)

            # I - Formula for hourly ET0 [mm/hour]
            ET0[j] = (0.408 * delta[j] * SommeRn[j] + gamma[j] * (37 / (Thr[j] + 273)) * u2[j] * (eThr[j] - ea[j])) / (
                    delta[j] + gamma[j] * (1 + 0.34 * u2[j]))

            # K - Rain for each hour - Pluie [mm/h]
            somme = 0
            length_result = len(result[4].get('datapoints'))
            for i in range(length_result - (60 * 24) + (j * 60) + 1, length_result - ((23 - j) * 60)):
                # Dividing by 60 because we cumulate rain intensity
                Pluvio = somme + result[4].get('datapoints')[i][0] / 60
                Pluie[j] = Pluvio * Area

        print''
        print "Recorded weather data for the last 24h :"
        print "========================================"
        print "   * Total radiation was :            ", round(sum(SommeRn), 2),   " MJ/(m2 day)"
        print "   * Mean temperature was :           ",round(sum(Thr)/24, 2),     " degree C"
        print "   * Mean vapor pressure was :        ",round(sum(ea)/24, 2),      " kPa"
        print "   * Mean wind speed for was :        ",round(sum(u2)/24, 2),      " m/s"
        print "   * Mean atmospheric pressure was :  ",round(sum(P)/24, 2),       " kPa"

        print "   * Yesterday it rained :            ",round(sum(Pluie)/Area,2), " mm"
        print "   * The ET0 for yesterday was :      ",round(sum(ET0), 2),        " mm"

        print''
        print('Irrigation decision :')
        print('=====================')

        print '* Average WC probe signal =', round(averageHUM456, 2), ' V'
        print '* The water content in the wall today is approximated to', int(VWC), "%"
        print '* Irrigation will start if water content is lower than', int(Water_Content_Limit), '%'

        if Irrig_Needed:

            print('* Irrigation is needed')

            # Computation of total water dose to apply - Dosis[L]
            Dose = sum(ET0) * Kl * Area - sum(Pluie)
            if Dose < 0:
                Dose = 0
                print "* No water has to be applied today, net water flux through the pot for the last 24h is negative "

            print "* The dose of water to apply today is ", round(Dose, 3), "L"

            # Valve opening time - t[sec]
            t = (Dose / Q)*60

            print "* The valve will be opened for", round(t/60, 2), " minutes"

            print "* This calculation is made for a Kl of ", Kl
            print "* If canopy cover has evolved on the module this value might have to be updated"

            timestamp = get_timestamp()
            # erase the current file and open the valve in 30 seconds
            open("valve.txt", 'w').write(str(timestamp + 30) + ";1\n")
            # append to the file and close the valve t+30 minute later
            open("valve.txt", 'a').write(str(timestamp + int(t) + 30) + ";0\n")
            print("* Irrigation has been programmed")

        else:
            print '* Irrigation is NOT needed'
            print '* Within', int(waiting_time / 3600), 'hours, water content will be checked again'

        # sleep for 'irrigation time PLUS x hours'
        sys.stdout.flush()
        if not test :
            time.sleep(waiting_time)

    ###############################
    #    POST IRRIGATION CHECK    #
    ###############################

    if HUM_QualCheck == True:

        print ""
        print 'Post-watering check :'
        print '====================='

        print
        #TODO
        timestamp = get_timestamp()
        print 'It is now', time.strftime('%I:%M%p', time.localtime(timestamp))
        print '* Watering has been done', int(waiting_time / 3600), "hours ago, it will now be checked if extra water is needed"
        print'* Data is being collected over', int(N), 'minutes...'

        # Get WC measures during 5 minutes
        ##################################

        dataFile = None

        # pre allocation
        Last_WC_HUM4 = range(0, N)
        Last_WC_HUM5 = range(0, N)
        Last_WC_HUM6 = range(0, N)

        # reading HUM values during 5 minutes for all 3 HUM sensors
        for i in range(0, N):
            # HUM4
            try:  # urlopen not usable with "with"
                url = "http://" + host + "/api/get/%21s_HUM4"

                # get datapoint for HUM sensor
                dataFile = urllib.urlopen(url, None, 20)

                # store it
                data = dataFile.read(80000)

                Last_WC_HUM4[i] = data

            except:
                print(u"URL=" + (url if url else "") + \
                      u", Message=" + traceback.format_exc())

            # HUM5
            try:  # urlopen not usable with "with"
                url = "http://" + host + "/api/get/%21s_HUM5"

                # get datapoint for HUM sensor
                dataFile = urllib.urlopen(url, None, 20)

                # store it
                Last_WC_HUM5[i] = dataFile.read(80000)

            except:
                print(u"URL=" + (url if url else "") + \
                      u", Message=" + traceback.format_exc())

            # HUM6
            try:  # urlopen not usable with "with"
                url = "http://" + host + "/api/get/%21s_HUM6"

                # get datapoint for HUM sensor
                dataFile = urllib.urlopen(url, None, 20)

                # store it
                Last_WC_HUM6[i] = dataFile.read(80000)

            except:
                print(u"URL=" + (url if url else "") + \
                      u", Message=" + traceback.format_exc())

            # Pour avoir  les messages dans nohup.out
            sys.stdout.flush()

            # sleep for 1 minutes (until next measure is recored)
            if not test :
                time.sleep(60)

        # Mean WC over 5 minutes
        somme = 0
        for i in range(1, N):
            # little trick to remove extra quotes (otherwise under the form '"str"' not readable)...
            WC = Last_WC_HUM4[i]
            somme = somme + float(WC[1:len(WC) - 1])
        Last_WC_HUM4_mean = somme / (N-1)

        somme = 0
        for i in range(1, N):
            WC = Last_WC_HUM5[i]
            somme = somme + float(WC[1:len(WC) - 1])
        Last_WC_HUM5_mean = somme / (N-1)

        somme = 0
        for i in range(1, N):
            WC = Last_WC_HUM6[i]
            somme = somme + float(WC[1:len(WC) - 1])
        Last_WC_HUM6_mean = somme / (N-1)

        # Mean values of the 3 sensors
        Last_WC_mean = (Last_WC_HUM4_mean + Last_WC_HUM5_mean + Last_WC_HUM6_mean) / 3
        Last_VWC = m_calib * Last_WC_mean + p_calib


        # QUALITY CHECK post irrig check
        ################################
        # pre allocations
        SCE_WC4 = 0
        SCE_WC5 = 0
        SCE_WC6 = 0
        for i in range(0, N):
            # Sum of deviations calculation
            WC = Last_WC_HUM4[i]
            SCE_WC4 = SCE_WC4 + pow(float(WC[1:len(WC) - 1]) - Last_WC_HUM4_mean, 2)
            WC = Last_WC_HUM5[i]
            SCE_WC5 = SCE_WC5 + pow(float(WC[1:len(WC) - 1]) - Last_WC_HUM5_mean, 2)
            WC = Last_WC_HUM6[i]
            SCE_WC6 = SCE_WC6 + pow(float(WC[1:len(WC) - 1]) - Last_WC_HUM6_mean, 2)
        # Std computation
        std_WC4 = math.sqrt((1/(float(N)-1)) * SCE_WC4)
        std_WC5 = math.sqrt((1/(float(N)-1)) * SCE_WC5)
        std_WC6 = math.sqrt((1/(float(N)-1)) * SCE_WC6)

        # TODO check std over space...
        std_WC456 = math.sqrt((1/float(2)) * (pow((Last_WC_HUM4_mean - Last_WC_mean), 2) + pow((Last_WC_HUM5_mean - Last_WC_mean), 2) + pow(
            (Last_WC_HUM6_mean - Last_WC_mean), 2)))

        print '* Reliability of the collected data will determined'
        print '  Here is the standard deviation over the last', int(N), 'minutes for the HUM sensors :'

        print '   * HUM4   :  ', round(std_WC4, 3)
        print '   * HUM5   :  ', round(std_WC5, 3)
        print '   * HUM6   :  ', round(std_WC6, 3)

        # TODO over space of the last measure ?
        print '  Here is the standard deviation over space for HUM sensors :'
        print '   * HUM456 :  ', round(std_WC456, 3)

    # TODO add condition for space reliability check
        if std_WC4 < LIM_HUM4 and std_WC5 < LIM_HUM5 and std_WC6 < LIM_HUM6:

            print "* The probes are still working"
            print "* Post watering check can be processed"

            print '* Average WC probe signal =', round(Last_WC_mean, 2), 'V'
            print '* Water content is now at', int(Last_VWC), '%'

            # Determine if additional watering is needed
            if Last_VWC < Water_Content_Limit:
                print '* This is too low, extra water is needed'

                # Calculation of additional watering needed
                Dose = (Water_Content_Limit * Pot_volume - Last_VWC * Pot_volume)/100

                # Calculation of irrigation time (seconds)
                t = (Dose / Q)*60
                print '* An additional', round(Dose,2), 'L is needed'
                print '* The valve will be opened for', round(t/60,2), 'more minutes today'

                # make irrigation happen
                timestamp = get_timestamp()
                # erase the current file and open the valve in 30 seconds
                open("valve.txt", 'a').write(str(timestamp + 30) + ";1\n")
                # append to the file and close the valve X minute later
                open("valve.txt", 'a').write(str(timestamp + int(t) + 30) + ";0\n")
                print("* Extra watering has been programmed")
            else:
                print('* This is sufficient, no extra watering is needed')
        else:
            print "* The probes are not working anymore, post watering check is not possible today"
            print "* A technical check up of the sensors is required"

    ##################################################################
    #  DEFAULT IRRIGATION if WC probes and weather station are down  #
    ##################################################################

    if HUM_QualCheck == False and WS_QualCheck == False:
        print('* Both water content probes and weather station are out of use')
        timestamp = get_timestamp()
        open("valve.txt", 'w').write(str(timestamp + 30) + ";1\n")
        open("valve.txt", 'a').write(str(int(timestamp + default_irrig) + 30) + ";0\n")
        print '* A security watering has been processed'
        print '* The valve will be opened for', round(default_irrig/60, 2), 'minutes today'
        print '* Nevertheless, a check up of the monitoring system is needed'

    print('This is it for today, new watering will start tomorrow at 6AM')

    # Pour avoir  les messages dans nohup.out
    sys.stdout.flush()

    # Shut down script until the next day
    now = get_timestamp()
    time_to_sleep = tomorrow - now
    if  test:
        break
    else :
        time.sleep(time_to_sleep)
