import json
import socket
import select
import errno
import sys
import threading as thread
from tkinter import *
import tkinter.font as tkFont
from enum import Enum

def checksum(data):  # Form the standard IP-suite checksum
    pos = len(data)
    if (pos & 1):  # If odd...
        pos -= 1
        sum = ord(data[pos])  # Prime the sum with the odd end byte
    else:
        sum = 0

    #Main code: loop to calculate the checksum
    while pos > 0:
        pos -= 2
        sum += (ord(data[pos + 1]) << 8) + ord(data[pos])

    sum = (sum >> 16) + (sum & 0xffff)
    sum += (sum >> 16)

    result = (~ sum) & 0xffff  # Keep lower 16 bits
    result = result >> 8 | ((result & 0xff) << 8)  # Swap bytes
    return chr(result / 256) + chr(result % 256)

class MessageType(Enum):
    CONNECT = 'connect'
    USERSLIST = 'get_users'
    DISCONNECT = 'disconnect'
    Privatemsg = 'set_msg'
    Publicmsg = 'set_msg_all'
    GETLISTFILE = 'get_list_file'
    DOWNLOAD = 'download'
    PROCEED = 'proceed'
    ACK = 'Acknowledgement '


client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
port = 55000
server_ip = '127.0.0.1'  # server IP
client_socket.connect((server_ip, port))


class ChatGUI:
    def __init__(self):
        # Create a chat window and make it visible
        self.Chat_Window = Tk()
        self.Chat_Window.withdraw()

        # login window
        self.login = Toplevel()
        self.login.title("Login")
        self.login.resizable(width=False, height=False)
        self.login.configure(width=500, height=400)
        # create a Label
        self.pls = Label(self.login,
                         text="Welcome to the Chat!\n  Please Enter your Username",
                         justify=CENTER,
                         font="Arial 14 bold")

        self.pls.place(relheight=0.15,
                       relx=0.2,
                       rely=0.07)
        # create a Label
        self.labelName = Label(self.login,
                               text="Username: ",
                               font="Arial 13")

        self.labelName.place(relheight=0.2,
                             relx=0.1,
                             rely=0.2)

        # create a entry box for
        # tying the message
        self.username = Entry(self.login,
                              font="Arial 15")

        self.username.place(relwidth=0.3,
                            relheight=0.10,
                            relx=0.35,
                            rely=0.2,
                            )

        # set the focus of the cursor
        # self.username.focus()

        # create a Continue Button
        # along with action
        self.login_button = Button(self.login,
                                   text="CONTINUE",
                                   font="Arial 15 bold",
                                   command=lambda: self.Login(self.username.get()))

        self.login_button.place(relx=0.4,
                                rely=0.55)
        self.Chat_Window.mainloop()

    # receive and send message from/to different user/s

    def Login(self, UserName):
        user_connect = {
            "type": str(MessageType['CONNECT'].name),
            "username": UserName,
        }
        user_connect = json.dumps(user_connect)
        client_socket.send(user_connect.encode('UTF-8'))
        self.login.destroy()
        self.ChatRoom_Gui(UserName)
        recieve_thread = thread.Thread(target=self.recieve_msg)
        recieve_thread.start()

    # The main layout of the chat
    def ChatRoom_Gui(self, name):
        HeadFont = tkFont.Font(family="Arial", size=16, weight="bold", slant="italic")
        ChatFont = tkFont.Font(family="Arial", size=14)
        SendFont = tkFont.Font(family="Arial", size=10, weight="bold")
        img = PhotoImage(file="background.png")
        self.Chat_Window.config(bg='LightSkyBlue2')  # bg='LightSkyBlue2'
        self.name = name
        # to show chat window
        img = PhotoImage(file="background.png")
        self.Chat_Window.deiconify()
        self.Chat_Window.title("CHATROOM")
        self.Chat_Window.resizable(width=True,
                                   height=True)

        self.Chat_Window.geometry("800x600")
        self.user_option_label = Label(self.Chat_Window,
                                       bg='LightSkyBlue2')  # bg="#6173A4"
        self.user_option_label.pack(side=RIGHT)
        self.labelHead = Label(self.Chat_Window,
                               bg='LightSkyBlue2',
                               text="Username:" + self.name,
                               font=HeadFont,
                               pady=3)

        self.labelHead.place(relwidth=1)

        self.Chat_log = Text(self.Chat_Window,
                             width=20,
                             height=2,
                             bg='LightSkyBlue2',
                             font=ChatFont,
                             padx=3,
                             pady=3)

        self.Chat_log.place(relheight=0.650,
                            relwidth=0.8,
                            rely=0.08)

        self.labelBottom = Label(self.Chat_Window,
                                 bg='LightSkyBlue2',
                                 height=110,
                                 width=80)

        self.file = Label(self.Chat_Window,
                          bg='LightSkyBlue2',
                          text="name:",
                          anchor=W,
                          font=ChatFont,
                          height=110,
                          width=80)

        self.file.place(relwidth=1,
                        relheight=0.08,
                        rely=0.820)

        self.file_box = Entry(self.file,
                              bg='light grey',
                              font=ChatFont)

        self.labelBottom.place(relwidth=1,
                               relheight=0.08,
                               rely=0.900)

        self.file_box.place(relwidth=0.30,
                            relheight=0.8,
                            rely=0.020,
                            relx=0.08)

        self.Msg_box = Entry(self.labelBottom,
                             bg='light grey',
                             font=ChatFont)

        # place the given widget
        # into the gui window
        self.Msg_box.place(relwidth=0.74,
                           relheight=0.9,
                           rely=0.008,
                           relx=0.004)

        self.Msg_box.focus()

        # create a Send Button
        self.buttonMsg = Button(self.labelBottom,
                                text="Send",
                                font=SendFont,
                                width=20,
                                bg='SlateGray4',
                                command=lambda: self.sendButton(self.Msg_box.get()))

        self.buttonMsg.place(relx=0.77,
                             rely=0.008,
                             relheight=0.7,
                             relwidth=0.22)

        self.file_button = Button(self.file,
                                  text="download",
                                  font=SendFont,
                                  width=20,
                                  bg='SlateGray4',
                                  command=lambda: self.download_Button(self.file_box.get()))

        self.file_button.place(relx=0.40,
                               rely=0.40,
                               anchor=W,
                               relheight=0.7,
                               relwidth=0.22)

        self.UserList = Button(self.user_option_label,
                               text="User List",
                               font=SendFont,
                               width=15,
                               bg='SlateGray4',
                               pady=10,
                               command=lambda: self.userList_serverList_button(0))
        self.UserList.pack(padx=3, pady=3)
        self.Server_files = Button(self.user_option_label,
                                   text="Show ServerFiles",
                                   font=SendFont,
                                   width=15,
                                   bg='SlateGray4',
                                   pady=10,
                                   command=lambda: self.userList_serverList_button(1))
        self.Server_files.pack(padx=3, pady=3)
        # create a scroll bar
        scrollbar = Scrollbar(self.Chat_log)

        # place the scroll bar
        # into the gui window
        scrollbar.pack(side=RIGHT, fill=Y)  # .place(relheight=1,
        #                 relx=0.974)

        scrollbar.config(command=self.Chat_log.yview, bg='SlateGray4', activebackground='SlateGray4')

        self.Chat_log.config(state=DISABLED)

    # If the user list button or the server files button is pressed send a Userlist msg request or server list msg
    # request depends on the type that entered 0=Userlist 1=Server files
    def userList_serverList_button(self, type: int):
        if type == 0:
            self.msg = MessageType.USERSLIST.name
        else:
            self.msg = MessageType.GETLISTFILE.name
        send_thread = thread.Thread(target=self.send_msg)
        send_thread.start()

    # function to basically start the thread for sending messages
    def sendButton(self, msg):
        # get a msg that was entered in the text box and send her
        self.Chat_log.config(state=DISABLED)  # prevent typing in the chat log.
        self.msg = str(msg)
        self.Msg_box.delete(0, END)
        send_thread = thread.Thread(target=self.send_msg)
        send_thread.start()

    def download_Button(self, msg):
        # get a msg that was entered in the text box and send her
        self.Chat_log.config(state=DISABLED)  # prevent typing in the chat log.
        self.msg = "+" + str(msg)
        self.file_box.delete(0, END)
        send_thread = thread.Thread(target=self.send_msg)
        send_thread.start()

    def download_file(self, server_port):
        UDPClientSocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        UDPClientSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        dest=(server_ip, server_port)
        UDPClientSocket.bind(dest)
        connection=("Connected")
        UDPClientSocket.sendto(connection.encode('UTF-8'),dest)
        expection_seq = 0
        while True:
            msg,address = UDPClientSocket.recvfrom(1024)
            check_sum=msg["checksum"]
            seq=msg["id"]
            data=msg["data"]
            with open(msg["filename",'ab']) as file:
                if checksum(data) == check_sum:
                    msg={
                        "type":MessageType.ACK.name,
                        "msg":"ACK" + seq ,
                        "checksum":checksum("ACK" + seq)
                    }
                    msg=json.dumps(msg)
                    UDPClientSocket.sendto(msg, dest)
                    file.write(data)
                if seq == str(expection_seq):
                    expecting_seq = 1 - expecting_seq
                else:
                    negative_seq = str(1 - expecting_seq)
                    msg={
                        "type":MessageType.ACK.name,
                        "msg":"neg" + negative_seq ,
                        "checksum":checksum("ACK" + seq)
                    }
                    msg = json.dumps(msg)
                    UDPClientSocket.sendto(msg,dest)
                #UDPClientSocket.sendto(msg,dest)

    def recieve_msg(self):
        self.Chat_log.config(state=NORMAL)  # Allow to change the chat log when a new msg arrive
        self.Chat_log.insert(END,
                             "Welcome to the Server! You can now chat\n")
        self.Chat_log.config(state=DISABLED)
        while True:
            try:  # Receive
                meg_recv = client_socket.recv(1024)
                # meg_recv = meg_recv.decode('UTF-8')
                meg_recv = json.loads(meg_recv)
                if not len(meg_recv):  # if you recieved an 0 length msg from the server
                    print("connection closed by server")
                    sys.exit()
                # username_length = int(username_header.decode('UTF-8'))
                msg_type = meg_recv['type']
                if msg_type == MessageType.DOWNLOAD.name:
                    server_port = meg_recv['msg']
                    self.download_file(server_port)
                self.Chat_log.config(state=NORMAL)
                self.Chat_log.insert(END,
                                     meg_recv['msg'] + "\n")
                self.Chat_log.config(state=DISABLED)
                # elif msg_type == MessageType.Publicmsg.name or msg_type == MessageType.Privatemsg.name or msg_type == MessageType.USERSLIST.name:
                #     self.Chat_log.config(state=NORMAL)
                #     self.Chat_log.insert(END,
                #                          meg_recv['msg'] + "\n")
                #     self.Chat_log.config(state=DISABLED)

            except IOError as e:
                if e.errno != errno.EAGAIN and e.errno != errno.EWOULDBLOCK:
                    print('Reading error', str(e))
                    sys.exit()
                continue
            except Exception as e:
                print('General error', str(e))
                sys.exit()
                pass

    def send_msg(self):
        self.Chat_log.config(state=DISABLED)
        while True:
            if self.msg:  # send
                if self.msg.startswith('@PM['):  # Check if its a PM
                    split_msg = self.msg.split()
                    if split_msg[0].endswith(']'):
                        to = split_msg[0]
                        to = to[4:len(to) - 1]
                        PM_msg = {
                            "type": str(MessageType.Privatemsg.name),
                            "username": str(self.name),
                            "recipient": to,
                            "msg": str(self.msg[len(split_msg[0]):])
                        }
                        PM_msg = json.dumps(PM_msg)
                        client_socket.send(PM_msg.encode('UTF-8'))
                elif self.msg == MessageType.USERSLIST.name:  # Check if its a User_list request
                    User_req = {
                        "type": str(MessageType.USERSLIST.name)
                    }
                    PM_msg = json.dumps(User_req)
                    client_socket.send(PM_msg.encode('UTF-8'))
                elif self.msg == MessageType.GETLISTFILE.name:  # Check if its a File server request
                    User_req = {
                        "type": str(MessageType.GETLISTFILE.name)
                    }
                    PM_msg = json.dumps(User_req)
                    client_socket.send(PM_msg.encode('UTF-8'))
                elif self.msg.startswith('+'):
                    file_name = self.msg[1:]
                    msg = {"type": str(MessageType.DOWNLOAD.name),
                           "msg": file_name}
                    down_msg = json.dumps(msg)
                    client_socket.send(down_msg.encode('UTF-8'))
                else:
                    send_msg = {
                        "type": str(MessageType['Publicmsg'].name),
                        "username": str(self.name),
                        "msg": str(self.msg)
                    }
                    send_msg = json.dumps(send_msg)
                    client_socket.send(send_msg.encode('UTF-8'))
            break


g = ChatGUI()
client_socket.close()
