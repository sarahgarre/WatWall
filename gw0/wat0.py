import socket
import os

DIR_BASE = os.path.normpath("~")
if not os.path.samefile(os.getcwd(), DIR_BASE):
     os.chdir(DIR_BASE)
print os.getcwd()

pid = str(os.getpid())
_lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)

try:
     _lock_socket.bind('\0GW0')
     print ('Socket GW0 now locked for process #'+pid)
     file("pid.txt", 'w').write(pid)
except socket.error:
     current = file("pid.txt", 'r').read()
     print ('GW0 lock exists for process #'+current+" : may be you should kill it!")
     sys.exit()

