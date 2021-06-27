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
log_f = 0

def router(id):
    ip = '127.0.0.' + str(id + 2)
    udp_port = PORTS_START - id
    neighbors = []
    n_udp_port = []
    # connect with tcp to Manager
    f = open('router{0}.txt'.format(id), 'a')

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    while True:
        try:
            s.connect(('127.0.0.1', PORTS_START + id))
            s.sendall(bytes(PORTS_START - id))
            neighbors = s.recv(1024)
            f.write('Connectivity Table: ' + repr(list(neighbors)) + '\n')
            f.flush()
            # cal neighbors udp_port
            for index, val in enumerate(neighbors):
                if MAX_COST > val > 0:
                    n_udp_port.append(PORTS_START - index)
            f.write('UDPS TO Connect: ' + str(n_udp_port) + '\n')
            f.flush()
        except:
            pass


def manager_tcp(i):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', PORTS_START + i))
    s.listen()
    conn, addr = s.accept()
    # save log for Starting TCP to Router
    log_f.write('Starting TCP connection R {0}\n'.format(i))
    log_f.flush()
    with conn:
        print('Connected by', addr)
        udp_port = conn.recv(1024)
        conn.sendall(bytes(manager_tcp_shared[i]))
        print('Router Config ' + str(i) + ' Sent')
        # save log for Connectivity Table to Router
        log_f.write('Connectivity Table R {0}\n'.format(i))
        log_f.flush()


def main():
    global manager_tcp_shared
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
        d = [[MAX_COST if i != j else 0 for i in range(routers_cnt)] for j in range(routers_cnt)]

        for line in f.readlines():
            inputs = line.split(sep=' ')
            d[int(inputs[0])][int(inputs[1])] = int(inputs[2])
            d[int(inputs[1])][int(inputs[0])] = int(inputs[2])

    # print read file
    print(d)
    # save log for reading config
    log_f.write('Read Config\n')
    log_f.flush()

    # fill connectity tables for routers
    manager_tcp_shared = [d[i] for i in range(routers_cnt)]
    # instantiate routers
    for i in range(routers_cnt):
        print('Router' + str(i))
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
        print('TCP Manager' + str(i))
        newt = threading.Thread(target=manager_tcp, args=(i,), daemon=True)
        newt.start()
        tcp_s.append(newt)

    # read packet sending orders
    with open('orders.txt') as f_orders:
        for line in f_orders.readlines():
            inputs = line.strip().split(sep=' ')
            orders.append([inputs[0],inputs[1]])
    print(orders)

    # send relative packets to routers

    # send quit order
if __name__ == '__main__':
    main()
