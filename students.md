# Program architecture WatWall

We have 2 computers
* a local computer that collects the data (AKUINO with ELSA-local)
* a (virtual) university server on which we copy the data and which allows to execute programs making decisions on when to irrigate (with ELSA - central & a wat1/2/3.py program)


Depending on whether you are in group 1, 2 or 3, you are interested in files and directories ending with 1, 2 or 3.
In GitHub sarahgarre/WatWall/gw2, for example, group 2 will put their Python program in the wat2.py file. An dummy file to start from is already there.Do not remove existing code in this dummy, as it ensures that your program only works in one copy and can be stopped if needed.

# Connection to the server 
[Link to server](http://greenwall.gembloux.uliege.be)

Three users (gw1, gw2, gw3) have been defined with their passwords. The connection is made with any computer with "rsh" software (e.g. PuTTY under Windows, rsh under Linux). You can download and install Putty [here](https://www.putty.org/).

To connect to the server, launch Putty and type: 

> rsh gw2@greenwall.gembloux.uliege.be

Then give your password (as sent to each group by the teacher).

# Creation of your scheduling program wat1/2/3.py

Your program must be in written Python and named watX.py (X=1, 2 or 3)
It must be pushed to the GitHub project sarahgarre/WatWall/gwX project (X=1, 2 or 3) in the corresponding team folder (gwx). This can be done for example by connecting to your GitHub account through PyCharm. 

# Execution of your program

You then get a "command line" terminal. To do things, you must type a command and then press enter. For example: 

* `./upd.sh` this script allows to bring back ALL the modifications of ALL the groups from GitHub.
* `./clean.sh` this script stops your program completely.
* `./run.sh` this script will stop your program if it works and restart it. Your program is in the background and you can log out.
* `./look.sh` allows you to see what's in the file that will be sent for valve control (valve.dat) and any error messages from your program in the background (nohup.out).
* `cat WatWall/watX.py` (X=1, 2 or 3) allows you to view your program on the server.

The file "valve.dat" must contain your commands to open and close the valves.
It is composed of independent lines each indicating a timestamp, a separating semicolon, 0 or 1 (closed / open) and an end of line ( \n ).
For example:
> 1580906117;1
> 1580906177;0
The timestamp is the number of seconds since 01/01/1970. It is calculated with the functions of the "time" module.

We put an example of "WatWall/gwX/watX.py" to get you started in your corresponding team folder. It is here you have to make calculations based on the data and make decisions to irrigate.

The command:
`> ls -l -t`
lists your files and gives you their size and modification date.


# Obtain data from the sensors connected to your AKUINO central
Each sensor has a specific name (e.g. HUM1 for the 1st humidity sensor).

The URL:
`> http://localhost/api/get/%21s_HUM1`
allows you to obtain the last value read for this sensor. We put an example in your WatWall/gwX/watX.py file to give you an idea of how to access.
