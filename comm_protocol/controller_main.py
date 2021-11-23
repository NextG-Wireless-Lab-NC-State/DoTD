from socket import *
import subprocess
import time
import sys
import control_mgs_pb2 as ControlMsg

serverAddressPort   = ("255.255.255.255", 20001)
bufferSize          = 1024

def establish_connection():
    UDPClientSocket = socket(family=AF_INET, type=SOCK_DGRAM)
    UDPClientSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    UDPClientSocket.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
    print "Controller - Agent Socket is open"
    return UDPClientSocket

def create_message(name, to, command, args_list):
    send_msg             = ControlMsg.control_msg()
    send_msg.cmd_name    = name
    send_msg.cmd_receiver= to
    send_msg.cmd         = command
    parameters           = send_msg.cmd_param.add()
    for i in range(len(args_list)):
        if i==0:parameters.arg1 = args_list[i]
        if i==1:parameters.arg2 = args_list[i]
        if i==2:parameters.arg3 = args_list[i]
        if i==3:parameters.arg4 = args_list[i]
        if i==4:parameters.arg5 = args_list[i]
        if i==5:parameters.arg6 = args_list[i]

    return send_msg.SerializeToString()

def send_command(message_to_send, socket):
    socket.sendto(message_to_send, serverAddressPort)

UDPClientSocket = establish_connection()
msg = create_message("Assign IP", "SAT12", "ifconfig", ["sat-eth1", "120.10.1.1/20"])
send_command(msg, UDPClientSocket)
