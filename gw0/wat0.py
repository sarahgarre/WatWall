import socket
import os

# Run only ONCE: Check if /run/akuino/ELSA.pid exists...
# pid = str(os.getpid())
# self.pidfile = self.HardConfig.RUNdirectory+"/ELSA.pid"
##
# if os.path.isfile(self.pidfile):
# print "%s already exists, exiting" % self.pidfile
# sys.exit()
# file(self.pidfile, 'w').write(pid)
# Without holding a reference to our socket somewhere it gets garbage
# collected when the function exits
_lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)

try:
     _lock_socket.bind('\0GW0')
     print ('Socket GW0 now locked')
except socket.error:
     print ('GW0 lock exists')
     sys.exit()

if not os.path.samefile(os.getcwd(), DIR_BASE):
     os.chdir(DIR_BASE)

print os.getcwd()
