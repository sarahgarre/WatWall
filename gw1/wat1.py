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
test = False

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

    # Recueil des dernières valeurs de tension des capteurs d'humidité
    dataFile = None
    humidite= [[] for b in range(2)]  # liste stockant les dernières valeurs d'humidité avant puis après irrigation
    for g in range(1, 4):  # boucle collectant les 3 dernières valeurs de nos capteurs d'humidité
        try:  # urlopen not usable with "with"
            url = "http://" + host + "/api/get/%21s_HUM" + unicode(g)
            dataFile = urllib.urlopen(url, None, 20)
            data = dataFile.read(80000)
            humidite[0].append((float(data.strip(delimiters))))  # ajout de la valeur receuillie en fin de liste
        except:
            print(u"URL=" + (url if url else "") + \
                  u", Message=" + traceback.format_exc())
        if dataFile:
            dataFile.close()

    # Conversion des tensions en teneur en eau puis trie de celles-ci par ordre croissant
    for o in range(0, 3):
        humidite[0][o] = ((35.24 * humidite[0][o] - 15.44) / (humidite[0][o] - 0.3747)) / 100
    humidite[0].sort()  # trie les valeurs d'humidité dans l'ordre croissant

    # Vérification des données d'humidité
    t=0
    if humidite[0][1]-humidite[0][0]>0.08 : # regarde si la différence entre la plus petite valeur et la valeur centrale est strictement supérieure à 8%
        del humidite[0][0]
        t=1
    elif humidite[0][2]-humidite[0][1]>0.08:
        del humidite[0][2]
        t+=2

    # Permet d'afficher le nombre de données supprimées
    if t==3: # correspond à l'effacement de 2 données
        z=2
    elif t==2: # correspond à l'effacement du max mais ce n'est qu'une donnée
        z=1
    else:
        z=t # sinon le t correspond au nombre de données supprimées
    print("Pour les capteurs d'humidités,"+str(z)+" "+"données ont été supprimées")

    # Combien de valeurs reste-t-il ?
    if t!=3:
        moyenne_humidite=[sum(humidite[0])/len(humidite[0])]
        print("On effectue le plan A et la teneur en eau moyenne est de"+" "+str(moyenne_humidite[0]))

        # Où se situe l'humidité moyenne ?
        if moyenne_humidite[0]>0.285: # regarde si elle est supérieure à la CC
            V_irrigation=0 # y'a assez d'eau on n'irrigue pas
            print("Irriguer n'est pas nécessaire, on est au dessus de la CC")
        else:
            V_irrigation = (0.285 - moyenne_humidite[0]) * 12.6 # volume d'irrigation nécessaire pour atteindre la CC
            print("On va irriguer"+" "+str(V_irrigation)+" litres pour atteindre la CC")
    else:
        print("Trop de problèmes avec nos valeurs des capteurs d'humidité, on passe au plan B")
        # Receuil des données météo des 24 dernières heures et nécessaires au calcul de l'ETP
        dataFile = None
        meteo = [[] for i in range(6)]  # tableau permettant le stockage des valeurs receuillies
        j = 0  # variable de changement de colonne dans le tableau
        try:  # urlopen not usable with "with"
            url = "http://" + host + "/api/grafana/query"
            now = get_timestamp()
            gr = {'range': {'from': formatDateGMT(now - (24 * 60 * 60)), 'to': formatDateGMT(now)}, \
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
                        meteo[j].append(
                            float(value))  # ajoute les données dans le tableau en dernière ligne de la colonne j
                    j += 1  # permet de passer à la colonne suivante
        except:
            print(u"URL=" + (url if url else "") + \
                  u", Message=" + traceback.format_exc())
        if dataFile:
            dataFile.close()

        # Calcul de l'ETP des 24 dernières heures
        ET0 = 0  # initialisation de la valeur de ET0
        Kc = 1  # valeur du coefficient cultural
        v = []  # variable permettant de trouver la taille de ma boucle for car sur 24h il se peut que l'on ne collecte pas exactement 1440 valeurs, cela évite donc de faire planter ma boucle for
        for i in range(0, len(
                meteo)):  # stocke dans ma liste le nombre de données collectées sur l'heure précédente pour chaque capteur
            v.append(len(meteo[i]))
        for q in range(0, min(v)):  # calcul de l'ET0 par minute avec les données précédemment collectées dans meteo
            delta = (4098 * (0.6108 * math.exp((17.27 * meteo[2][q]) / (meteo[2][q] + 237.3)))) / (
                    (meteo[2][q] + 237.3) ** 2)
            es = 100 * meteo[3][q] / meteo[5][q]
            ea = meteo[3][q]
            altitude = 106  # pour Mont-Saint-Guilbert (159 si Gembloux)
            albedo = 0.2
            Rs = meteo[0][q] * 10 ** (-6) * 60
            Rns = (1 - albedo) * Rs
            lat = 50
            sigma = 4.903 * 10 ** (-9) / (24 * 60)
            J = (date.today() - date(2020, 1,1)).days + 1  # représente le nombre de jours passés depuis le 1er janvier 2020 compris
            dr = 1 + 0.033 * math.cos((6.28 / 365) * J)
            declinaison = 0.409 * math.sin((6.28 / 365) * J - 1.39)
            ws = math.acos(-math.tan(lat) * math.tan(declinaison))
            Ra = (1/ 3.14) * 0.082 * dr * (ws * math.sin(lat) * math.sin(declinaison) + math.sin(ws) * math.cos(lat) * math.cos(declinaison))
            Rso = (0.75 + 210 ** (-5) * altitude) * Ra
            Rnl = sigma * (meteo[2][q] + 273.15) * (0.34 * 0.14 * ea ** 0.5) * (1.35 * (Rs / Rso) - 0.35)
            Rn = Rns - Rnl
            gamma = 0.665 * meteo[4][q] * 10 ** (-3)
            vitesse_du_vent = meteo[1][q]
            ET0 += (0.408 * delta * Rn + gamma * (0.625 / (273 + meteo[2][q])) * vitesse_du_vent * (es - ea)) / (delta + gamma * (1 + 0.34 * vitesse_du_vent))  # stocke la somme des ET0 calculés pour chaque minute
        print("L'ET0 calculé sur les 24 dernières heures est de"+" "+str (ET0)+" "+"mm")

        if 0<ET0<8:
            print("On effectue donc le plan B")
            ETR = ET0 * Kc  # valeur réelle de l'ETP en considérant le type et le stade de la culture
            V_irrigation = ETR * 10 ** (-2) * 10.5 # volume qui a été perdu par évapotranspiration
            moyenne_humidite[0]= humidite[0]
            print("On va donc irriguer"+" "+str(V_irrigation)+" "+"litres pour compenser l'ETP des 24 dernières heures")
            print("La teneur en eau moyenne est de"+" "+str(moyenne_humidite[0]))
        else:
            print("On effectue donc le plan C")
            ET0=float(open("../WatWall/gw1/ET0.csv", 'r').read().split("\n")[J - 1]) # trouve la valeur moyenne d'ET0 pour aujourd'hui dans notre fichier
            print("On prend donc"+" "+str(ET0)+"comme valeur d'ET0 à la place")
            ETR = ET0 * Kc
            V_irrigation = ETR * 10 ** (-2) * 10.5
            moyenne_humidite[0] = humidite[0]

    # Le volume d'eau est-il suffisant ?
    if V_irrigation < 0.025:  # regarde si le volume à irriguer est assez important, on fait cela à cause de l'incertitude de précision d'arrosage des petits volumes
        print("Le volume d'eau à irriguer est insuffisant, aucune irrigation n'est appliquée ")
        sys.stdout.flush()  # permet de regarder aux messages
        time.sleep(24 * 60 * 60)  # ce n'est pas le cas donc on irrigue pas et on attend le jour suivant
    else:
        # Planning d'irrigation
        temps_irrigation = round(V_irrigation / 0.000416)  # calcul le temps correspondant au volume précédemment calculé
        print("On va donc ouvrir les vannes pendant"+" "+str(temps_irrigation)+" "+"secondes soit environ"+" "+str(round(temps_irrigation/60))+" "+"minutes")
        timestamp = get_timestamp()
        n = 0
        if temps_irrigation <= 1200:
            open("valve.txt", 'w').write(str(timestamp) + ";1\n")  # crée un nouveau planning et demande d'ouvrir la vanne à l'instant même
            open("valve.txt", 'a').write(str(timestamp + temps_irrigation) + ";0\n")  # demande la fermeture de la vanne après le temps d'irrigation calculé plus haut
        else:
            open("valve.txt", 'w').write(str(timestamp) + ";1\n")
            open("valve.txt", 'a').write(str(timestamp + temps_irrigation) + ";0\n")
            temps_irrigation -= 1200
            n = 1
            while temps_irrigation > 1200:  # implémente le temps non applicable dans cette heure aux heures d'après
                open("valve.txt", 'a').write(str(timestamp + n * 3600) + ";1\n")
                open("valve.txt", 'a').write(str(timestamp + n * 3600 + 1200) + ";0\n")
                temps_irrigation -= 1200
                n += 1
            open("valve.txt", 'a').write(str(timestamp + n * 3600) + ";1\n")
            open("valve.txt", 'a').write(str(timestamp + n * 3600 + temps_irrigation) + ";0\n")
        if n==0:
            print("On peut donc uniquement irriguer sur l'heure actuelle")
        else:
            print("On va donc irriguer sur"+" "+str(n+1)+" "+"heures différentes")
        sys.stdout.flush()
        time.sleep(4*60*60) # fait une pause dans l'éxécution de 4h pour que l'eau atteigne les capteurs d'humidité


        # Vérification pour voir si l'irrigation a bien été effectuée

        # Recueil des nouvelles dernières valeurs de tension des capteurs d'humidité
        dataFile = None
        for g in range(1, 4):  # boucle collectant les 3 dernières valeurs de nos capteurs d'humidité
            try:  # urlopen not usable with "with"
                url = "http://" + host + "/api/get/%21s_HUM" + unicode(g)
                dataFile = urllib.urlopen(url, None, 20)
                data = dataFile.read(80000)
                humidite[1].append((float(data.strip(delimiters))))  # ajout de la valeur receuillie en fin de liste
            except:
                print(u"URL=" + (url if url else "") + \
                        u", Message=" + traceback.format_exc())
            if dataFile:
                dataFile.close()

        # Conversion des tensions en teneur en eau
        for o in range(0, 3):
            humidite[1][o] = ((35.24 * humidite[1][o] - 15.44) / (humidite[1][o] - 0.3747)) / 100
        humidite[1].sort()

        # Elimination des mêmes valeurs que la première fois et calcul de la nouvelle humidité moyenne
        if t==1:
            del humidite[1][0]
        elif t==2:
            del humidite[1][2]
        elif t==3:
            del humidite[1][0]
            del humidite[1][2]
        moyenne_humidite.append(sum(humidite[1]) / len(humidite[1]))
        print("La nouvelle teneur en eau moyenne est de"+" "+str(moyenne_humidite[1]))

        # Vérification de l'augmentation de l'humidité moyenne
        if moyenne_humidite[1] - moyenne_humidite[0] > 0:  # regarde si la différence d'humidité moyenne est positive, preuve qu'elle a bien eu lieu
            print("C'est donc plus élevé que 4 heures plus tôt, l'irrigation a fonctionné :)")
            sys.stdout.flush()
            time.sleep(20*60*60)  # fait une pause de 20h dans l'éxécution
        else:
            print("Aïe l'irrigation n'a pas fonctionné, bon bah on recommence:(") # si celle-ci n'a pas augmenté le programme recommence depuis le début des calculs







