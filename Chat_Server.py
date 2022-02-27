import _thread
import os
import socket, select
import json
from enum import Enum
import threading as thread
import base64


# os- provides functions for interacting with the operating system
# socket -way of connecting two nodes on a network to communicate with each other
# select - a direct interface to the underlying operating system implementation

def checksum(buffer):
    nleft = len(buffer)
    sum = 0
    pos = 0
    while nleft > 1:
        sum = ord(buffer[pos]) * 256 + (ord(buffer[pos + 1]) + sum)
        pos = pos + 2
        nleft = nleft - 2
    if nleft == 1:
        sum = sum + ord(buffer[pos]) * 256

    sum = (sum >> 16) + (sum & 0xFFFF)
    sum += (sum >> 16)
    sum = (~sum & 0xFFFF)

    return sum


class MessageType(Enum):
    CONNECT = 'connect'
    USERSLIST = 'get_users'
    DISCONNECT = 'disconnect'
    Privatemsg = 'set_msg'
    Publicmsg = 'set_msg_all'
    GETLISTFILE = 'get_list_file'
    DOWNLOAD = 'download'
    PROCEED = 'proceed'


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
    for clients in users_List:
        clients.send(message)


# (sock, recv, message)- sock - socket of the sender , recv - the recipient ..
def PM(sock, recv, message):
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
    recv_UDP_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    UDP_port = 55001
    isconnected = False
    while not isconnected:
        try:
            recv_UDP_sock.bind((server_ip, UDP_port))
            isconnected = True
        except:
            print("Bind failed")
            UDP_port += 1

    UDP_dic = {
        "type": MessageType.DOWNLOAD.name,
        "msg": UDP_port
    }
    UDP_dic = json.dumps(UDP_dic)
    C_socket.send(UDP_dic.encode('UTF-8'))
    connection = recv_UDP_sock.recvfrom(2048)
    try:
        with open("ServerFiles/" + filename, "rb") as file:  # open the file the client want
            data = file.read()  # as bytes!
    except Exception as e:
        err_msg={"type":MessageType.Privatemsg.name,
                 "msg": filename + "is not available in the server files!\n Try a different file name"}
        err_msg=json.dumps(err_msg)
        C_socket.send(err_msg.encode('UTF-8'))
        print("Fail", str(e))
    seq_num = 0
    each_seg_size = 1000  # size of each seg
    total_segment_size = 0
    all_segments = {}
    while total_segment_size < len(data):
        if total_segment_size + each_seg_size > len(data):
            segment = data[total_segment_size:]
        else:
            segment = data[total_segment_size:total_segment_size + each_seg_size]
        seq_num += 1
        all_segments[seq_num] = segment
        total_segment_size += each_seg_size

    for seg_id, seg in all_segments.items():
        ack_recv = False
        while not ack_recv:
            segment_as_str = base64.b64encode(seg).decode(
                'UTF-8')  # need to send a data as a str (cant json a byte object)
            msg = {
                "checksum": str(checksum(segment_as_str)),
                "id": str(seg_id),
                "length": len(all_segments),
                "data": segment_as_str,
                "filename": str(filename)
            }
            msg = json.dumps(msg)
            recv_UDP_sock.sendto(msg.encode('UTF-8'), connection[
                1])  # send the data to the client (connection[1] is the IP and port of the client)

            try:
                msg, address = recv_UDP_sock.recvfrom(2048)
            except socket.timeout:
                print("Time out")
            else:
                msg = json.loads(msg)
                print(msg)
                check_sum = msg["checksum"]
                ack_id = msg["id"]
                ack = msg["msg"]
                if checksum(ack) == check_sum and ack_id == str(seg_id):
                    ack_recv = True
                if ack.startswith("neg"):
                    ack_recv = False
        # seq_num = 1 - seq_num


def message_received(C_socket, C_address):
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
            print(e)
            print("Connection closed from " + users_List[sock])
            user_left = users_List[sock]
            socket_List.remove(sock)
            del users_List[sock]
            left_msg = {"type": str(MessageType.CONNECT.name),
                        "msg": user_left + " has left the chat"}
            left_msg = json.dumps(left_msg)
            broadcast(left_msg.encode('UTF-8'))

        if not len(message_dict):
            print("Connection closed from " + users_List[sock])
            user_left = users_List[sock]
            socket_List.remove(sock)
            del users_List[sock]
            left_msg = {"type": str(MessageType.CONNECT.name),
                        "msg": user_left + " has left the chat"}
            left_msg = json.dumps(left_msg)
            broadcast(left_msg.encode('UTF-8'))
            return False

    except:
        print("Connection closed from " + users_List[sock])
        user_left = users_List[sock]
        socket_List.remove(sock)
        del users_List[sock]
        left_msg = {"type": str(MessageType.CONNECT.name),
                    "msg": user_left + " has left the chat"}
        left_msg = json.dumps(left_msg)
        broadcast(left_msg.encode('UTF-8'))
        return False


while True:
    ready_to_read, ready_to_write, in_error = select.select(socket_List, [], [], 0)
    for sock in ready_to_read:
        if sock == server_socket:  # if a user just connected to the server
            C_socket, C_address = server_socket.accept()
            message_received(C_socket, C_address)
            print(
                "You are connected from:" + str((C_address[0])) + ":" + str(C_address[1]) + " your user name is: " +
                users_List[C_socket])
        else:  # If someone is already connected
            # message = message_received(sock, C_address)
            message = _thread.start_new_thread(message_received, (sock, C_address))
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
