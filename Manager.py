import os
import sys
import time
import threading
import socket

from multiprocessing import Process
from multiprocessing import set_start_method

PROJECT_PATH = 'D:/Uni-Courses/Network/Final-Pro/'
MAX_COST = 99
PORTS_START = 65432

manager_tcp_shared = []
routers_acked_l = threading.Lock()
routers_acked = 0
log_f = 0

def router(id):
    udp_ip = '127.0.0.' + str(id + 2)
    udp_port = PORTS_START - id - 1
    neighbors = []
    n_udp_port = []
    n_udp_ip = []
    # list of udp sockets
    socs = []
    f = open('router{0}.txt'.format(id), 'a')
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # connect with tcp to Manager
        s.connect(('127.0.0.1', PORTS_START + id))
        # send UDP port to manager
        s.sendall(bytes(PORTS_START - id - 1))
        # get connectivity table
        neighbors = s.recv(1024)
        f.write('Connectivity Table: ' + repr(list(neighbors)) + '\n')
        f.flush()
        # send ready sig to manager
        s.sendall(b'ready')
        status = s.recv(1024)
        f.write('Status From Manager: ' + repr(str(status)) + '\n')
        f.flush()
        # cal neighbors udp_port
        for index, val in enumerate(neighbors):
            if MAX_COST > val > 0:
                n_udp_port.append(PORTS_START - index - 1)
                n_udp_ip.append('127.0.0.' + str(index + 2))
        f.write('UDPS TO Connect: ' + str(n_udp_port) + '\n')
        f.flush()
        # setup router server udp
        soc = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        soc.bind((udp_ip, udp_port))
        # setup udp connection
        for ip,port in zip(n_udp_ip,n_udp_port):
            soc_t = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
            # Listen for incoming datagrams
            soc_t.sendto(str.encode('ack from {0} to {1}'.format(id,PORTS_START-port-1)), (ip, port))
            socs.append(soc_t)

        for port in n_udp_port:
            f.write(str(soc.recvfrom(1024)[0])+'\n')
            f.flush()
        # tell manager all neighbors are ok
        s.sendall(b'Acked')
        status = s.recv(1024)
        f.write('Status From Manager: ' + repr(str(status)) + '\n')
        f.flush()

        # send LSP to all neighbors

    except Exception as e:
        print(e.with_traceback())

def manager_tcp(i):
    global routers_acked
    global manager_tcp_shared
    global routers_acked_l
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', PORTS_START + i))
    s.listen()
    conn, addr = s.accept()
    # save log for Starting TCP to Router
    log_f.write('Starting TCP connection R {0}\n'.format(i))
    log_f.flush()
    try:
        udp_port = conn.recv(1024)
        conn.sendall(bytes(manager_tcp_shared[i]))

        # save log for Connectivity Table to Router
        log_f.write('Connectivity Table R {0}\n'.format(i))
        log_f.flush()

        # send safety message
        ready_sig = conn.recv(1024)
        conn.sendall(b'safe')
        log_f.write('Safe for R {0}\n'.format(i))
        log_f.flush()

        # acked and ready for routing
        ready_sig = conn.recv(1024)
        routers_acked_l.acquire()
        routers_acked -= 1
        routers_acked_l.release()
        while routers_acked != 0:
            pass
        conn.sendall(b'route!!')
        log_f.write('Ready to Route Sent for R {0}\n'.format(i))
        log_f.flush()

        #
    except Exception as e:
        print(e.with_traceback())


def main():
    global manager_tcp_shared
    global routers_acked
    # keeping distances
    d = []
    # routers ip and ports
    ips = []
    tcp_ports = []
    # threads list
    t = []
    # TCP Sockets to Routers
    tcp_s = []
    # routers counts
    routers_cnt = 0
    # packets send list
    orders = []
    # log file for manager
    global log_f
    log_f = open('manager.txt', 'a')
    with open('config.txt') as f:
        routers_cnt = int(f.readline())
        routers_acked = routers_cnt
        d = [[MAX_COST if i != j else 0 for i in range(routers_cnt)] for j in range(routers_cnt)]

        for line in f.readlines():
            inputs = line.split(sep=' ')
            d[int(inputs[0])][int(inputs[1])] = int(inputs[2])
            d[int(inputs[1])][int(inputs[0])] = int(inputs[2])

    # print read file
    # print(d)
    # save log for reading config
    log_f.write('Read Config\n')
    log_f.flush()

    # fill connectity tables for routers
    manager_tcp_shared = [d[i] for i in range(routers_cnt)]
    # instantiate routers
    for i in range(routers_cnt):
        # print('Router' + str(i))
        # save log for creating routers
        log_f.write('Created Router {0}\n'.format(i))
        log_f.flush()

        newt = threading.Thread(target=router, args=(i,), daemon=True)
        newt.start()
        t.append(newt)
        ips.append('127.0.0.' + str(i + 2))
        tcp_ports.append(str(PORTS_START + i))
    # connect with tcp to routers
    for i in range(routers_cnt):
        # print('TCP Manager' + str(i))
        newt = threading.Thread(target=manager_tcp, args=(i,), daemon=True)
        newt.start()
        tcp_s.append(newt)

    # read packet sending orders
    with open('orders.txt') as f_orders:
        for line in f_orders.readlines():
            inputs = line.strip().split(sep=' ')
            orders.append([inputs[0],inputs[1]])
    # print(orders)

    while True:
        pass
    # send relative packets to routers

    # send quit order
if __name__ == '__main__':
    main()
