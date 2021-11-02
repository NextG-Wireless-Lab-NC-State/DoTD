
import socket
import subprocess
import time
sys.path.append('../templates')
import control_mgs_pb2 as ControlMsg

serverAddressPort   = ("131.227.207.157", 20001)
bufferSize          = 1024

test_msg = ControlMsg.control_msg()
test_msg.cmd_id = 1
test_msg.cmd = "ping"

parameters          = test_msg.cmd_param.add()
parameters.arg1     = "-c10"
parameters.arg2     = "131.227.207.231"
message_to_send     = test_msg.SerializeToString()
#bytesToSend         = str.encode(str(message_to_send))


def main():
    UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    while True:
	UDPClientSocket.sendto(message_to_send, serverAddressPort)
	time.sleep(15)

