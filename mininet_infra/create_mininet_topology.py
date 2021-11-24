from mininet.net import Mininet
from mininet.node import Node, OVSKernelSwitch, Controller, RemoteController
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.link import *
from mininet.topo import Topo
from mininet.log import setLogLevel, info
import socket
import time
import subprocess
import threading
import os
import sys
sys.path.append('../comm_protocol')
import c_m_update_topology_pb2 as updateTopologyMsg

class LinuxRouter( Node ):	# from the Mininet library
    "A Node with IP forwarding enabled."

    def config( self, **params ):
        super( LinuxRouter, self).config( **params )
        # Enable forwarding on the router
        info ('enabling forwarding on ', self)
        self.cmd( 'sysctl net.ipv4.ip_forward=1' )

    def terminate( self ):
        self.cmd( 'sysctl net.ipv4.ip_forward=0' )
        super( LinuxRouter, self ).terminate()


class sat_network(Topo):
    def __init__(self, **kwargs):
        super(sat_network, self).__init__(**kwargs)

    def rp_disable(self, host):
    	ifaces = host.cmd('ls /proc/sys/net/ipv4/conf')
    	ifacelist = ifaces.split()    # default is to split on whitespace
    	for iface in ifacelist:
		if iface != 'lo': host.cmd('sysctl net.ipv4.conf.' + iface + '.rp_filter=0')

    def set_default_gw_gs(self, net, gs_list):
        for gs in gs_list:
            ground_station = net.getNodeByName(gs)
            print ground_station.IP()


    def create_sat_network(self, satellites, ground_stations, connectivity_matrix):
        sat_list = []
        gs_list  = []
        links    = []
        mgnt_intf = []
        s1 = self.addSwitch('s1')
        sat_intf_count = []
        sat_intf_count = [1 for i in range(len(satellites))]

        cnt_ip = 0
        for i in range(0, len(satellites)):
            ip_control_intf_oct3 = (i+4)/254
            ip_control_intf_oct4 = (i+4)%254
            # , ip="192.168."+str(ip_control_intf_oct3)+"."+str(ip_control_intf_oct4)
            sat_name = self.addHost('sat'+str(i), cls=LinuxRouter, ip="172.16."+str(ip_control_intf_oct3)+"."+str(ip_control_intf_oct4)+"/16")
            self.addLink(sat_name, s1, cls=TCLink)
            sat_list.append(sat_name)
            mgnt_intf.append({"node":'sat'+str(i), "mgnt_ip": "172.16."+str(ip_control_intf_oct3)+"."+str(ip_control_intf_oct4)})
            cnt_ip = i

        for i in range(0, len(ground_stations)):
            ip_control_intf_oct3 = (i+4+len(satellites))/254
            ip_control_intf_oct4 = (i+4+len(satellites))%254
            # , ip="192.168."+str(ip_control_intf_oct3)+"."+str(ip_control_intf_oct4)
            gs_name = self.addHost('gs'+str(i), ip="172.16."+str(ip_control_intf_oct3)+"."+str(ip_control_intf_oct4)+"/16")
            self.addLink(gs_name, s1, cls=TCLink)
            mgnt_intf.append({"node":'gs'+str(i), "mgnt_ip": "172.16."+str(ip_control_intf_oct3)+"."+str(ip_control_intf_oct4)})
            gs_list.append(gs_name)

        connectivity_matrix_temp = connectivity_matrix
        for i in range(0,len(connectivity_matrix_temp)):
            for j in range(0, len(connectivity_matrix_temp[i])):
                # Add the ISL links
                if i < len(satellites) and j < len(satellites) and connectivity_matrix_temp[i][j] == 1:
                    self.addLink(sat_list[i], sat_list[j], intfname1 = 'sat'+str(i)+'-eth'+str(sat_intf_count[i]), inftname2 = 'sat'+str(j)+'-eth'+str(sat_intf_count[j]), cls=TCLink)
                    links.append('sat'+str(i)+'-eth'+str(sat_intf_count[i])+":"+'sat'+str(j)+'-eth'+str(sat_intf_count[j]))

                    connectivity_matrix_temp[i][j] = 0
                    connectivity_matrix_temp[j][i] = 0

                    sat_intf_count[i] = sat_intf_count[i] + 1
                    sat_intf_count[j] = sat_intf_count[j] + 1

                # Add the GSL links
                if i < len(satellites) and j >= len(satellites) and connectivity_matrix_temp[i][j] == 1:
                    gid = j - len(satellites)
                    self.addLink(sat_list[i], gs_list[gid], intfname1 = 'sat'+str(i)+'-eth'+str(sat_intf_count[i]), inftname2 = 'gs'+str(gid)+'-eth1', cls=TCLink)
                    links.append('sat'+str(i)+'-eth'+str(sat_intf_count[i])+":"+ 'gs'+str(gid)+'-eth1')

                    connectivity_matrix_temp[i][j] = 0
                    connectivity_matrix_temp[j][i] = 0

                    sat_intf_count[i] = sat_intf_count[i] + 1

        return {
        	"sat_list": sat_list,
        	"gs_list": gs_list,
            "links": links,
            "intf_count_sats": sat_intf_count,
            "management_interface": mgnt_intf
    	}

    def get_management_ip(self, all_mgnt_ips, node):
        for interface in all_mgnt_ips:
            if interface["node"] == node:
                return interface["mgnt_ip"]


    def run_topology_commands(self, net, command, node1, node2):
        net_node1 = net.getNodeByName(node1)
        net_node2 = net.getNodeByName(node2)

        if command == "deleteLink":
            if net.linksBetween(net_node1, net_node2):
                net.delLinkBetween(net_node1, net_node2)

        if command == "addLink":
            net.addLink(net_node1, net_node2, cls=TCLink)

    def handle_topology_updates_commands(self, net):
        UDPSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        UDPSocket.bind(("172.16.0.3", 20001))
        print "listener on 0.3 is created"
        while(True):
            bytesAddressPair = UDPSocket.recvfrom(1024)
            print bytesAddressPair
            recv_msg = updateTopologyMsg.c_m_update_topology()
            recv_msg.ParseFromString(bytesAddressPair[0])
            t = threading.Thread(target=handle_commands, args=(net, recv_msg.command, recv_msg.node1_name, recv_msg.node2_name))
            t.start()

    def startListener(self, net, satellites, ground_stations, intfs):
        for i in range(len(satellites)):
            sat_node = net.getNodeByName("sat"+str(i))
            node_m_ip = self.get_management_ip(intfs, "sat"+str(i)).strip()
            print("added .....,"+node_m_ip+" \n")
            sat_node.cmd("python ../comm_protocol/satellite_agent.py "+node_m_ip+ " &")

        for i in range(len(ground_stations)):
            gs_node = net.getNodeByName("gs"+str(i))
            node_m_ip = self.get_management_ip(intfs, "gs"+str(i)).strip()
            gs_node.cmd("python ../comm_protocol/satellite_agent.py "+node_m_ip+ " &")

        mininet_topology_listner = threading.Thread(target=self.handle_topology_updates_commands, args=(net,))
        mininet_topology_listner.start()
