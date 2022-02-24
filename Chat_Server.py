import os
import socket, select
import json
from enum import Enum
# os- provides functions for interacting with the operating system
# socket -way of connecting two nodes on a network to communicate with each other
# select - a direct interface to the underlying operating system implementation

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
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)#s = socket(domain(AF_INET-Internet domain), type, protocol)
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


def message_received(C_socket):
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
                PM(C_socket, users_List[C_socket], message.encode('UTF-8')
            # elif message_type==MessageType.DOWNLOAD.name:


        except Exception as e:
            print(e)

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
