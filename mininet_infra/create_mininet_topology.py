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
import math
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


    def create_sat_network(self, satellites, ground_stations, connectivity_matrix, link_throughput, link_latency):
        sat_list = []
        gs_list  = []
        links    = []
        mgnt_intf = []
        cnt_ip = 0

        sat_intf_count = [1 for i in range(len(satellites))]
        s1 = self.addSwitch('s1')


        # create satellites node
        for i in range(0, len(satellites)):
            ip_control_intf_oct3 = (i+5)/254
            ip_control_intf_oct4 = (i+5)%254
            sat_name = self.addHost('sat'+str(i), cls=LinuxRouter, ip="172.16."+str(ip_control_intf_oct3)+"."+str(ip_control_intf_oct4)+"/16")
            self.addLink(sat_name, s1, cls=TCLink)
            sat_list.append(sat_name)
            mgnt_intf.append({"node":'sat'+str(i), "mgnt_ip": "172.16."+str(ip_control_intf_oct3)+"."+str(ip_control_intf_oct4)})
            cnt_ip = i

            # sat_name = self.addHost('sat'+str(i), cls=LinuxRouter)
            # sat_list.append(sat_name)

        # create ground-stations node
        for i in range(0, len(ground_stations)):
            ip_control_intf_oct3 = (i+5+len(satellites))/254
            ip_control_intf_oct4 = (i+5+len(satellites))%254
            # , ip="192.168."+str(ip_control_intf_oct3)+"."+str(ip_control_intf_oct4)
            gs_name = self.addHost('gs'+str(i), ip="172.16."+str(ip_control_intf_oct3)+"."+str(ip_control_intf_oct4)+"/16")
            self.addLink(gs_name, s1, cls=TCLink)
            mgnt_intf.append({"node":'gs'+str(i), "mgnt_ip": "172.16."+str(ip_control_intf_oct3)+"."+str(ip_control_intf_oct4)})
            gs_list.append(gs_name)

            # gs_name = self.addHost('gs'+str(i))
            # gs_list.append(gs_name)

        connectivity_matrix_temp = connectivity_matrix[:]
        for i in range(0,len(connectivity_matrix_temp)):
            for j in range(0, len(connectivity_matrix_temp[i])):
                # if connectivity_matrix_temp[i][j] == 1:
                #     print i,j
                # Add the ISL links
                if i < len(satellites) and j < len(satellites) and connectivity_matrix_temp[i][j] == 1:
                    self.addLink(sat_list[i], sat_list[j], intfname1 = 'sat'+str(i)+'-eth'+str(sat_intf_count[i]), inftname2 = 'sat'+str(j)+'-eth'+str(sat_intf_count[j]), cls=TCLink, delay=str(link_latency[i][j])+'ms')
                    links.append('sat'+str(i)+'-eth'+str(sat_intf_count[i])+":"+'sat'+str(j)+'-eth'+str(sat_intf_count[j]))

                    connectivity_matrix_temp[i][j] = 0
                    connectivity_matrix_temp[j][i] = 0

                    sat_intf_count[i] = sat_intf_count[i] + 1
                    sat_intf_count[j] = sat_intf_count[j] + 1

                # Add the GSL links
                if i < len(satellites) and j >= len(satellites) and connectivity_matrix_temp[i][j] == 1:
                    gid = j - len(satellites)
                    self.addLink(sat_list[i], gs_list[gid], intfname1 = 'sat'+str(i)+'-eth'+str(sat_intf_count[i]), inftname2 = 'gs'+str(gid)+'-eth1', cls=TCLink, delay=str(link_latency[i][j])+'ms')
                    links.append('sat'+str(i)+'-eth'+str(sat_intf_count[i])+":"+ 'gs'+str(gid)+'-eth1')

                    connectivity_matrix_temp[i][j] = 0
                    connectivity_matrix_temp[j][i] = 0

                    sat_intf_count[i] = sat_intf_count[i] + 1

        return {
        	"sat_list": sat_list,
        	"gs_list": gs_list,
            "isl_gls_links": links,
            "intf_count_sats": sat_intf_count,
            "management_interface": mgnt_intf
    	}

    def get_network_address(self, str_ip_address):
        # Assuming /28 subnet mask
        ip_oct1, ip_oct2, ip_oct3, ip_oct4 = str_ip_address.split(".")
        net_add1= int(ip_oct1) & 255
        net_add2= int(ip_oct2) & 255
        net_add3= int(ip_oct3) & 255
        net_add4= int(ip_oct4) & 240

        return str(net_add1)+"."+str(net_add2)+"."+str(net_add3)+"."+str(net_add4)

    def configure_initial_static_route(self, net, route, num_of_satellites, num_of_ground_stations, cmds_list):
        if len(route) > 2:
            src_node, next_hop_node, dest_node, last_hop_node = route[0], route[1], route[len(route)-1], route[len(route)-2]

            src_node_prefix  = "gs" if src_node >= num_of_satellites else "sat"
            dest_node_prefix = "gs" if dest_node >= num_of_satellites else "sat"

            src_node_m      = net.getNodeByName(src_node_prefix+str(src_node%num_of_satellites))
            next_hop_node_m = net.getNodeByName("sat"+str(next_hop_node%num_of_satellites))
            first_hop_link  = net.linksBetween(src_node_m, next_hop_node_m)[0]

            dest_node_m     = net.getNodeByName(dest_node_prefix+str(dest_node%num_of_satellites))
            last_hop_node_m = net.getNodeByName("sat"+str(last_hop_node%num_of_satellites))
            last_hop_link   = net.linksBetween(last_hop_node_m, dest_node_m)[0]

            src_dev, src_via = (str(first_hop_link.intf1), str(first_hop_link.intf2.IP())) if str(src_node_m.name) in str(first_hop_link.intf1) else (str(first_hop_link.intf2), str(first_hop_link.intf1.IP()))
            dest_dev, dest_via = (str(last_hop_link.intf2), str(last_hop_link.intf1.IP())) if str(dest_node_m.name) in str(last_hop_link.intf2) else (str(last_hop_link.intf1), str(last_hop_link.intf2.IP()))

            cmd_on_src_node     = "ip route add "+ self.get_network_address(last_hop_link.intf1.IP())+"/28 via "+src_via+" dev "+src_dev+" & "
            cmd_on_dest_node    = "ip route add "+ self.get_network_address(first_hop_link.intf1.IP())+"/28 via "+dest_via+" dev "+dest_dev+" & "

            src_node_m.cmd(cmd_on_src_node)
            dest_node_m.cmd(cmd_on_dest_node)
            # print cmd_on_src_node
            # print cmd_on_dest_node

            # cmds_list[src_node].append(cmd_on_src_node)
            # cmds_list[dest_node].append(cmd_on_dest_node)

        else:
            print "No need to configure static route"

        # return cmds_list

    def run_static_update_commands(self, net, cmds_list, num_of_satellites):
        for i in range(len(cmds_list)):
            node_prefix  = "gs" if i >= num_of_satellites else "sat"
            node_m      = net.getNodeByName(node_prefix+str(i%num_of_satellites))
            all_cmds_per_node = ""
            for cmd in cmds_list[i]:
                all_cmds_per_node += cmd + " && "

            node_m.cmd(all_cmds_per_node)

    def initial_ipv4_assignment_for_interfaces(self, net, addresses_pool):
        list_of_Intf_IPs = []
        nodes = net.hosts
        for node in nodes:
            for intf in node.intfList():
                if "eth0" not in intf.name:
                    if intf.link:
                        intf1, intf2 = intf.link.intf1, intf.link.intf2
                        network_address = self.get_free_IP(addresses_pool)
                        if network_address != -1:
                            oct1, oct2, oct3, oct4 = network_address.split('.');
                            intf1.setIP(oct1+"."+oct2+"."+oct3+"."+str(int(oct4)+1)+"/28")
                            intf2.setIP(oct1+"."+oct2+"."+oct3+"."+str(int(oct4)+2)+"/28")

                            # Assign the default gw to the ground stations
                            if "gs" in node.name:
                                debug("route add default gw "+str(intf1.IP())+" dev "+node.name+"-eth0", intf2.IP())
                                node.cmd("route add default gw "+str(intf1.IP())+" dev "+node.name+"-eth0");
                        else:
                            print "[Create Sat Network -- GSL] No Available IPs to assign"
                            exit()

            self.rp_disable(node)

        with open('constellation_ip_assignment.txt', 'w') as f:
            for node in nodes:
                for intf in node.intfList():
                    if intf.link:
                        write_toFile = str(intf.link.intf1)+"\t"+str(intf.link.intf1.IP())+"\n"+str(intf.link.intf2)+"\t"+str(intf.link.intf2.IP())+"\n"
                        f.write(write_toFile)
                        list_of_Intf_IPs.append({"Interface": str(intf.link.intf1), "IP": str(intf.link.intf1.IP())+"/28"})
                        list_of_Intf_IPs.append({"Interface": str(intf.link.intf2), "IP": str(intf.link.intf2.IP())+"/28"})

        return list_of_Intf_IPs

    def get_free_IP(self, pool):
        free_ip = -1
        for i in pool:
            if i[0] == 1:
                free_ip = i[1]
                pool.remove(i)
                break;
        return free_ip

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
            net_node1.cmd("ifconfig")
            net_node2.cmd("ifconfig")
            net.addLink(net_node1, net_node2, cls=TCLink)

    def handle_topology_updates_commands(self, net):
        UDPSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        UDPSocket.bind(("", 20001))
        print "Mininet main listener is created ... "
        while(True):
            bytesAddressPair = UDPSocket.recvfrom(1024)
            recv_msg = updateTopologyMsg.c_m_update_topology()
            recv_msg.ParseFromString(bytesAddressPair[0])
            self.run_topology_commands(net, recv_msg.command, recv_msg.node1_name, recv_msg.node2_name)
            # t = threading.Thread(target=self.run_topology_commands, args=(net, recv_msg.command, recv_msg.node1_name, recv_msg.node2_name))
            # t.start()

    def startListener(self, net, satellites, ground_stations, intfs):
        for i in range(len(satellites)):
            sat_node = net.getNodeByName("sat"+str(i))
            node_m_ip = self.get_management_ip(intfs, "sat"+str(i)).strip()
            print("added .....,"+node_m_ip)
            sat_node.cmd("python ../comm_protocol/satellite_agent.py "+node_m_ip+ " &")

        for i in range(len(ground_stations)):
            gs_node = net.getNodeByName("gs"+str(i))
            node_m_ip = self.get_management_ip(intfs, "gs"+str(i)).strip()
            gs_node.cmd("python ../comm_protocol/satellite_agent.py "+node_m_ip+ " &")

        mininet_topology_listner = threading.Thread(target=self.handle_topology_updates_commands, args=(net,))
        mininet_topology_listner.start()

    def startworker(self, net, satellites, ground_stations, intfs):
        for i in range(len(satellites)):
            sat_node = net.getNodeByName("sat"+str(i))
            node_m_ip = self.get_management_ip(intfs, "sat"+str(i)).strip()
            print("added .....,"+"sat"+str(i)+" -- "+node_m_ip)
            sat_node.cmd("python ../comm_protocol/satellite_worker.py "+node_m_ip+ " &")

    def startRoutingConfig(self, net, satellites, ground_stations, intfs):
        patch_size = 10.0
        intervals = int(math.ceil(len(satellites)/float(patch_size)))
        print intervals
        remaining_sats = len(satellites)
        for v in range(intervals):
            start = int(v*patch_size)
            end = int((v+1)*patch_size) if remaining_sats>=patch_size else len(satellites)
            remaining_sats -= patch_size
            print "Run satellites from sat", start, " to sat", end, " The remaining sats = ", remaining_sats
            for i in range(start, end, 1):
                sat_node = net.getNodeByName("sat"+str(i))
                # print("Start routing config for .....,"+"sat"+str(i))
                sat_node.cmd("python ../comm_protocol/config_initial_routes.py "+"sat"+str(i)+" &")

            time.sleep(20)
            for i in range(start, end, 1):
                sat_node.cmd("pkill -f 'python ../comm_protocol/config_initial_routes.py sat"+str(i)+"'")
