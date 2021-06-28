import heapq
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

# shared vars
routers_cnt = 0
manager_tcp_shared = []
routers_acked_l = threading.Lock()
routers_safe_l = threading.Lock()
routers_acked = 0
routers_safe = 0
log_f = 0
man_order = {}

def router_tranmiter(soc,f,ft,n_udp_port,socs,n_udp_ip):
    packet = list(soc.recvfrom(1024)[0])
    if packet[1] == id:
        f.write('Packet rec from' + str(packet[2]) + ' ' + '\n')
        f.flush()
    else:
        next_id = ft[packet[1]][0]
        print(next_id)
        next_port = PORTS_START - next_id - 1
        next_index = n_udp_port.index(next_port)
        socs[next_index].sendto(bytes(packet), (n_udp_ip[next_index], next_port))
        f.write('Transit Packet ' + str(packet[2]) + ' to ' + str(packet[1]) + '\n')
        f.flush()


def dijkstra(graph, src, dest, visited, distances, predecessors):
    """ calculates a shortest path tree routed in src
    """
    # ending condition
    if src == dest:
        # We build the shortest path and display it
        path = []
        pred = dest
        while pred != None:
            path.append(pred)
            pred = predecessors.get(pred, None)
        # reverses the array, to display the path nicely
        path.pop()
        path.reverse()
        return path

    else:
        # if it is the initial  run, initializes the cost
        if not visited:
            distances[src] = 0
        # visit the neighbors
        for neighbor in graph[src]:
            if neighbor not in visited:
                new_distance = distances[src] + graph[src][neighbor]
                if new_distance < distances.get(neighbor, float('inf')):
                    distances[neighbor] = new_distance
                    predecessors[neighbor] = src
        # mark as visited
        visited.append(src)
        # now that all neighbors have been visited: recurse
        # select the non visited node with lowest distance 'x'
        # run Dijskstra with src='x'
        unvisited = {}
        for k in graph:
            if k not in visited:
                unvisited[k] = distances.get(k, float('inf'))
        x = min(unvisited, key=unvisited.get)
        return dijkstra(graph, x, dest, visited, distances, predecessors)


def router(id):
    udp_ip = '127.0.0.' + str(id + 2)
    udp_port = PORTS_START - id - 1
    neighbors = []
    n_udp_port = []
    n_udp_ip = []
    # list of udp sockets
    socs = []
    # distance vector for topology
    d_dic = {}
    # forwarding table
    ft = {}

    f = open('router{0}.txt'.format(id), 'a')
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # connect with tcp to Manager
        s.connect(('127.0.0.1', PORTS_START + id))
        # send UDP port to manager
        s.sendall(bytes(PORTS_START - id - 1))
        # get connectivity table
        neighbors = list(s.recv(1024))
        f.write('Connectivity Table: ' + repr(list(neighbors)) + '\n')
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
        # send ready sig to manager
        s.sendall(b'ready')
        status = s.recv(1024)
        f.write('Status From Manager: ' + repr(str(status)) + '\n')
        f.flush()
        # setup udp connections
        for ip, port in zip(n_udp_ip, n_udp_port):
            soc_t = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
            # Listen for incoming datagrams
            soc_t.sendto(str.encode('ack from {0} to {1}'.format(id, PORTS_START - port - 1)), (ip, port))
            socs.append(soc_t)

        for port in n_udp_port:
            f.write(str(soc.recvfrom(1024)[0]) + '\n')
            f.flush()
        # tell manager all neighbors are ok
        s.sendall(b'Acked')
        status = s.recv(1024)
        f.write('Status From Manager: ' + repr(str(status)) + '\n')
        f.flush()

        # send LSP to all neighbors
        d_dic[id] = list(neighbors)
        for soc_t, ip, port in zip(socs, n_udp_ip, n_udp_port):
            t_list = neighbors.copy()
            t_list.append(id)
            soc_t.sendto(bytes(t_list), (ip, port))
        f.write('Send LSP To Neighbors\n')
        f.flush()
        # receive and resend LSP to all neighbors
        while True:
            resp = list(soc.recvfrom(1024)[0])
            neigh_id = resp.pop()
            if neigh_id not in d_dic.keys():
                d_dic[neigh_id] = resp
            resp.append(neigh_id)
            for soc_t, ip, port in zip(socs, n_udp_ip, n_udp_port):
                soc_t.sendto(bytes(resp), (ip, port))
            if len(d_dic.items()) == routers_cnt:
                break
        # log network topology
        f.write(str(d_dic) + '\n')
        f.flush()
        # build graph
        graph = {}
        for key in d_dic.keys():
            graph[key] = {}
            for index, val in enumerate(d_dic.get(key)):
                if index >= routers_cnt:
                    break
                if MAX_COST > val > 0:
                    graph[key][index] = val
        # log graph network topology
        f.write(str(graph) + '\n')
        f.flush()
        # create SPT
        for i in range(routers_cnt):
            if i == id:
                ft[id] = [id]
            else:
                ft[i] = dijkstra(graph, id, i,[],{},{})

        f.write(str(ft))
        f.flush()
        # save SPT
        f_spt = open('routerSPT{0}.txt'.format(id), 'w')
        f_spt.write(str(ft))
        f_spt.flush()
        f_spt.close()
        # resend received packet
        # send or quit order from manager
        # newt = threading.Thread(target=router_tranmiter, args=(soc,f,ft,n_udp_port,socs,n_udp_ip,), daemon=True)
        # newt.start()
        s.settimeout(0.1)
        soc.settimeout(0.1)
        while True:
            try:
                order = s.recv(1024)
                if int(bytes.decode(order, encoding='UTF-8')) == MAX_COST:
                    f.write('Quit' + str(id) + '\n')
                    f.flush()
                    break
                else:
                    dest_id = int(bytes.decode(order, encoding='UTF-8'))
                    next_id = ft[dest_id][0]
                    next_port = PORTS_START - next_id - 1
                    next_index = n_udp_port.index(next_port)
                    packet = [223, dest_id, id]
                    socs[next_index].sendto(bytes(packet), (n_udp_ip[next_index], next_port))
                    f.write('Start Transmission Packet ' + str(id) + ' to ' + str(dest_id) + '\n')
                    f.flush()
            except Exception as e:
                pass
            try:
                packet = list(soc.recvfrom(1024)[0])
                if packet[1] == id:
                    f.write('Packet rec from' + str(packet[2]) + ' ' + '\n')
                    f.flush()
                else:
                    next_id = ft[packet[1]][0]
                    next_port = PORTS_START - next_id - 1
                    next_index = n_udp_port.index(next_port)
                    socs[next_index].sendto(bytes(packet), (n_udp_ip[next_index], next_port))
                    f.write('Transit Packet ' + str(packet[2]) + ' to ' + str(packet[1]) + '\n')
                    f.flush()
            except Exception as e:
                pass


        # closing thread
        soc.close()
        s.close()
        f.close()


    except Exception as e:
        print(e.with_traceback())


def manager_tcp(i):
    global routers_acked
    global manager_tcp_shared
    global routers_acked_l
    global routers_safe
    global routers_safe_l
    global man_order
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
        routers_safe_l.acquire()
        routers_safe -= 1
        routers_safe_l.release()
        while routers_safe != 0:
            pass
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

        # send order to dest
        while i not in man_order.keys():
            pass
        conn.sendall(str(man_order[i]).encode())
        log_f.write('Send Order R {0} msg {1}\n'.format(i, man_order[i]))
        log_f.flush()
        time.sleep(5.005)
        # send quit
        conn.sendall(str(man_order[i]).encode())
        log_f.write('Send Order R {0} msg {1}\n'.format(i, man_order[i]))
        log_f.flush()
    except Exception as e:
        print(e.with_traceback())


def main():
    global manager_tcp_shared
    global routers_acked
    global routers_cnt
    global routers_safe
    global man_order
    # keeping distances
    d = []
    # routers ip and ports
    ips = []
    tcp_ports = []
    # threads list
    t = []
    # TCP Sockets to Routers
    tcp_s = []
    # packets send list
    orders = []
    # log file for manager
    global log_f
    log_f = open('manager.txt', 'a')
    with open('config.txt') as f:
        routers_cnt = int(f.readline())
        routers_acked = routers_cnt
        routers_safe = routers_cnt
        d = [[MAX_COST if i != j else 0 for i in range(routers_cnt)] for j in range(routers_cnt)]

        for line in f.readlines():
            inputs = line.split(sep=' ')
            d[int(inputs[0])][int(inputs[1])] = int(inputs[2])
            d[int(inputs[1])][int(inputs[0])] = int(inputs[2])

    # save log for reading config
    log_f.write('Read Config\n')
    log_f.flush()

    # fill connectity tables for routers
    manager_tcp_shared = [d[i] for i in range(routers_cnt)]
    # instantiate routers
    for i in range(routers_cnt):
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
        newt = threading.Thread(target=manager_tcp, args=(i,), daemon=True)
        newt.start()
        tcp_s.append(newt)

    # read packet sending orders
    with open('orders.txt') as f_orders:
        for line in f_orders.readlines():
            inputs = line.strip().split(sep=' ')
            orders.append([int(inputs[0]), int(inputs[1])])


    # send relative packets to routers
    for order in orders:
        man_order[order[0]] = order[1]
    print(man_order)
    time.sleep(5)
    # send quit order
    for order in orders:
        man_order[order[0]] = MAX_COST
    time.sleep(0.005)

    while True:
        pass


if __name__ == '__main__':
    main()
