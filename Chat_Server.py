import _thread
import os
import socket, select
import json
from MessageTypes import MessageType
import base64
from CheckSum import checksum

# os- provides functions for interacting with the operating system
# socket -way of connecting two nodes on a network to communicate with each other
# select - a direct interface to the underlying operating system implementation

server_ip = '127.0.0.1'  # server IP
server_port = 55000  # Port
socket_List = []  # socket list of the server
users_List = {}
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM,
                              0)  # s = socket(domain(AF_INET-Internet domain), type, protocol)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((server_ip, server_port))
server_socket.listen(5)
socket_List.append(server_socket)


# method to send a message to all the clients together
def broadcast(message):
    """
    This function broadcast a message to all the user connected to the server
    :param message: the message
    :return: .
    """
    for clients in users_List:
        clients.send(message)


# (sock, recv, message)- sock - socket of the sender , recv - the recipient ..
def PM(sock, recv, message):
    """
    this funcion send private msg to the clients.
    :param sock: sender(socket!)
    :param recv: the username of the recipient
    :param message: the message the client wish to send
    :return: .
    """
    found = False
    sock.send(message)  # show the message to the sender
    if users_List[sock] == recv:  # if its a PM to himself.
        return
    for dest_sock, usernames in users_List.items():
        if usernames == recv:  # find the user that the PM is sent to
            found = True
            dest_sock.send(message)
    if not found:
        err = {"type": str(MessageType.CONNECT.name),
               "msg": f"The user {recv} is not in the server"}
        err = json.dumps(err)
        sock.send(err.encode('UTF-8'))


def UDP_file_sender(filename, C_socket):
    """
    This is the Reliable UDP file transfer.
    when the client wish to download a file its open a UDP connection with him.
    first it sends the port that the client need to connect to through the TCP socket.
    after the connection is established the server open the file the client wanted.
    if the file doesn't exist it send a msg that the file is not available.
    after that the program start splitting the file data to segments when each segment size start with 1000.
    it wrap the data with id and a checksum and send it to the client.
    if the client receive the data it send an ACK msg with the id number to the server.
    when the server receive the ack msg it increase each segment size so the downloading progress will be faster.
    when the client didn't receive the packet after the time out time it send the file again.
    if the server receive a neg ack msg it means that there was a problem with the sending,
    so it makes a new segment with smaller size.
    what the idea of the program is stop and wait arq with TCP congestion control
    :param filename: the file the user want
    :param C_socket: the TCP socket of the client
    :return:
    """
    recv_UDP_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    UDP_port = 55001
    isconnected = False
    # trying to find an available port for the client to connect
    while not isconnected:
        try:
            recv_UDP_sock.bind((server_ip, UDP_port))
            isconnected = True
        except:
            print("Bind failed")
            UDP_port += 1

    # send the port to the client
    UDP_dic = {
        "type": MessageType.DOWNLOAD.name,
        "msg": UDP_port
    }
    UDP_dic = json.dumps(UDP_dic)
    C_socket.send(UDP_dic.encode('UTF-8'))
    connection = recv_UDP_sock.recvfrom(65000)
    # open the file and read all the data
    try:
        with open("ServerFiles/" + filename, "rb") as file:  # open the file the client want
            data = file.read()  # as bytes!
    except Exception as e:
        # if the file dosent exist
        err_msg = {"type": MessageType.Privatemsg.name,
                   "msg": filename + "is not available in the server files!\n Try a different file name"}
        err_msg = json.dumps(err_msg)
        C_socket.send(err_msg.encode('UTF-8'))
        print("Fail", str(e))
    total_size = os.path.getsize("ServerFiles/" + filename)
    seq_num = 0
    each_seg_size = 1000  # size of each seg
    total_segment_size = 0
    first_send = True
    Failed = False
    change_mode = False
    ssthresh = 64000 / 2
    half_sent = False
    counter = 0
    last_fail = 53000
    CC = 1000  # the size to increase each time the server receive an ack
    while total_segment_size < len(data):
        # print("Last fail ", last_fail)
        # print("ssh ", ssthresh)
        if Failed:  # if the fail try to make a smaller segment
            change_mode = False  # Restart the congestion avoidance flag
            if total_segment_size - each_seg_size >= 0:
                total_segment_size -= each_seg_size
            else:
                total_segment_size = 0
            if each_seg_size >= ssthresh:
                # Fast recovery
                each_seg_size = int(last_fail / 3)
                CC = 2000
            else:
                each_seg_size = 1000
                CC = 2000
            Failed = False
        ack_recv = False
        # if this it the last segment
        if total_segment_size + each_seg_size > len(data):
            segment = data[total_segment_size:]

        else:
            # create a segment with the requested size
            # print(total_segment_size, total_segment_size + each_seg_size)
            segment = data[total_segment_size:total_segment_size + each_seg_size]
        # sequence number for each segment
        seq_num += 1
        # add the sement created to the total size sent untill now
        total_segment_size += each_seg_size
        # print("total sizee is", total_segment_size)
        # print("CC ", CC)
        print(each_seg_size)
        while not ack_recv or not Failed:
            if half_sent:
                recv_msg, address = C_socket.recvfrom(65000)
                recv_msg = json.loads(recv_msg)
                if recv_msg['type'] == MessageType.PROCEED.name:
                    half_sent = False
            segment_as_str = base64.b64encode(segment).decode(
                'UTF-8')  # need to send a data as a str (cant json a byte object)
            if first_send:
                # if its the first send add the file name and size to the json.
                seg_msg = {
                    "checksum": str(checksum(segment_as_str)),
                    "id": str(seq_num),
                    "data": segment_as_str,
                    "filename": str(filename),
                    "filesize": str(total_size)
                }
                first_send = False
            else:
                seg_msg = {
                    "checksum": str(checksum(segment_as_str)),
                    "id": str(seq_num),
                    "data": segment_as_str,
                }
            seg_msg = json.dumps(seg_msg)
            try:
                # check if the size is not bigger then the buffer
                # send the data to the client (connection[1] is the IP and port of the client)
                recv_UDP_sock.sendto(seg_msg.encode('UTF-8'), connection[1])
            except Exception as e:
                # if its fail to send, save the segment exit the While and create a new segment(line 137)
                print(e)
                CC = int(CC / 2)
                last_fail = each_seg_size
                ssthresh = int(last_fail / 2)
                Failed = True
                break
            # the time-out to receive an ack from the client
            recv_UDP_sock.settimeout(1)
            try:
                recv_msg, address = recv_UDP_sock.recvfrom(65000)
            except socket.timeout:
                # if there's a time-out go back to the start and send the segment again.
                print("Time out")
                CC = int(CC / 2)
                last_fail = each_seg_size
                ssthresh = int(last_fail / 2)
                Failed = True
            else:
                recv_msg = json.loads(recv_msg)
                # print(recv_msg)
                check_sum = recv_msg["checksum"]
                ack_id = recv_msg["id"]
                ack = recv_msg["msg"]
                # If the client receive an ack for the id the server send,
                # try to increase the segment size for a faster downloading
                if checksum(ack) == check_sum and ack_id == str(seq_num):
                    ack_recv = True
                    if total_segment_size >= total_size / 2 and counter == 0:
                        half_sent = True
                        counter = counter+1
                    if each_seg_size+1000 >= last_fail:  # if manage to pass the last fail increase the value
                        last_fail += 2000
                    elif each_seg_size >= last_fail - 10000:  # getting closer to the last fail
                        CC = 25  # try to get closer to the limit
                        each_seg_size += CC
                    elif each_seg_size >= ssthresh:  # Congestion avoidance
                        if not change_mode:
                            CC = int(CC / 2.5)
                            change_mode = True
                        each_seg_size += CC
                        CC += 250
                    else:
                        # Slow start
                        CC += 1000  # try to get closer to the limit
                        each_seg_size += CC
                    break
                # if we receive a neg ack then decrease the segment size (decrease the sending speed)
                elif ack.startswith("neg"):
                    ssthresh = int(last_fail / 2)
                    # CC = 1000
                    ack_recv = False
                    Failed = True
                    break


def message_received(C_socket):
    """
    This function receive the messages the client send.
    check the type of the message and execute the client request
    :param C_socket: client socket
    :return: True if it succeeded to execute the client request
             False if there was a problem/the client disconnected
    """
    try:
        message_dict = C_socket.recv(2048)
        message_dict = json.loads(message_dict)
        try:
            message_type = message_dict['type']
            if message_type == MessageType.CONNECT.name:  # if its a connect request
                socket_List.append(C_socket)  # add the user socket to the socket list and his name to the user list
                users_List[C_socket] = message_dict['username']
                connected_msg = {
                    "type": str(MessageType.CONNECT.name),
                    "msg": message_dict['username'] + " is now connected to the server!\n",
                }
                connected_msg = json.dumps(connected_msg)
                broadcast(connected_msg.encode('UTF-8'))  # Send a msg to all the users that a new user is connected
                return True
            elif message_type == MessageType.Publicmsg.name:  # send a public msg to all the users in the chat
                print(f"Received message from " + message_dict['username'] + ":" + message_dict['msg'])
                message = {'type': str(MessageType.Publicmsg.name),
                           "msg": message_dict['username'] + ":" + message_dict['msg']}
                message = json.dumps(message)
                broadcast(message.encode('UTF-8'))
                return True
            elif message_type == MessageType.Privatemsg.name:  # send a private msg
                message = {'type': str(MessageType.Privatemsg.name),
                           "msg": "PM-" + message_dict['username'] + ":" + message_dict['msg']}
                message = json.dumps(message)
                PM(C_socket, message_dict['recipient'], message.encode('UTF-8'))
                return True
            elif message_type == MessageType.USERSLIST.name:  # if there's a user list request
                users = '----Users Online:-----\n'
                for i in users_List.values():
                    users += i + '\n'
                users += '-----------------------\n'
                message = {"type": str(MessageType.USERSLIST.name),
                           "msg": users}
                message = json.dumps(message)
                PM(C_socket, users_List[C_socket], message.encode('UTF-8'))
            elif message_type == MessageType.GETLISTFILE.name:
                file_list = os.listdir("ServerFiles")
                files = "----Server Files----\n"
                for file in file_list:
                    files += file + "\n"
                files += '-----------------------\n'
                message = {"type": str(MessageType.GETLISTFILE.name),
                           "msg": files}
                message = json.dumps(message)
                PM(C_socket, users_List[C_socket], message.encode('UTF-8'))
            elif message_type == MessageType.DOWNLOAD.name:
                _thread.start_new_thread(UDP_file_sender, (message_dict['msg'], C_socket))
                # down_thread = thread.Thread(target=UDP_file_sender(message_dict['msg'], C_socket))
                # down_thread.start()
                return True


        except Exception as e:
            return False

        if not len(message_dict):
            return False

    except:
        return False


while True:
    ready_to_read, ready_to_write, in_error = select.select(socket_List, [], [], 0)
    for sock in ready_to_read:
        if sock == server_socket:  # if a user just connected to the server
            C_socket, C_address = server_socket.accept()
            message_received(C_socket)
            print(
                "You are connected from:" + str((C_address[0])) + ":" + str(C_address[1]) + " your user name is: " +
                users_List[C_socket])
        else:  # If someone is already connected
            # message = _thread.start_new_thread(message_received, (sock, C_address))
            message = message_received(sock)
            if message is False:
                print("Connection closed from " + users_List[sock])
                user_left = users_List[sock]
                socket_List.remove(sock)
                del users_List[sock]
                left_msg = {"type": str(MessageType.CONNECT.name),
                            "msg": user_left + " has left the chat"}
                left_msg = json.dumps(left_msg)
                broadcast(left_msg.encode('UTF-8'))
                continue

server_socket.close()
