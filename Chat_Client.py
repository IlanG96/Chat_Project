import base64
import json
import socket
from tkinter.ttk import Progressbar
from CheckSum import checksum
import errno
from tkinter import *
import tkinter.font as tkFont
import _thread
from MessageTypes import MessageType

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
port = 55000


class ChatGUI:
    server_ip = '127.0.0.1'  # server IP
    # If the user list button or the server files button is pressed send a Userlist msg request or server list msg
    # request depends on the type that entered 0=Userlist 1=Server files
    def userList_serverList_button(self, type: int):
        if type == 0:
            self.msg = MessageType.USERSLIST.name
        else:
            self.msg = MessageType.GETLISTFILE.name
        self.send_msg()

    def proceed_func(self):
        self.proceed_flag = True

    # function to basically start the thread for sending messages
    def sendButton(self, msg):
        # get a msg that was entered in the text box and send her
        self.Chat_log.config(state=DISABLED)  # prevent typing in the chat log.
        self.msg = str(msg)
        self.Msg_box.delete(0, END)
        self.send_msg()

    def download_Button(self, msg):
        # get a msg that was entered in the text box and send her
        self.Chat_log.config(state=DISABLED)  # prevent typing in the chat log.
        self.msg = "+" + str(msg)
        self.file_box.delete(0, END)
        self.send_msg()

    def download_file(self, server_port):
        """
        this function connect through a UDP connection to the server. and start receiving segments of the requested
        file. if the segment reciceved pass the check sum test the function send and ACK msg to the server. if the
        segment fail the check sum test it mean the segment is damaged so it send a neg ACK msg that mean the client
        didnt recieve a the segment.
         :param server_port: the port that the client connect to the server.
        :return:
        """
        counter = 0
        UDPClientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        dest = (self.server_ip, server_port)
        connection = "Connected"
        segments_recv = {}
        self.progress['value'] = 0
        # send a connected msg to the server so the server will have the client ip and port
        UDPClientSocket.sendto(connection.encode('UTF-8'), dest)
        expection_seq = 1
        segment_counter = 0
        total_recv_size = 0
        while True:
            if 0 < self.progress["value"] < 90 :
                self.file_button["state"] = "disabled"
            else:
                self.file_button["state"] = "normal"
            if self.progress["value"] < 50:
                self.proceedButton["state"] = "disabled"
            elif self.proceed_flag == False:
                self.proceedButton["state"] = "normal"
                self.Chat_log.config(state=NORMAL)  # Allow to change the chat log when a new msg arrive
                self.Chat_log.insert(END,
                                     "You downloaded 50% of the file\n Press proceed to continue\n")
                self.Chat_log.config(state=DISABLED)
                while self.proceed_flag == False:
                    continue
                proceed_msg = {
                    "type": MessageType.PROCEED.name
                }
                proceed_msg = json.dumps(proceed_msg)
                client_socket.sendto(proceed_msg.encode('UTF-8'), dest)

            try:  # get the msg from the server
                msg, address = UDPClientSocket.recvfrom(65000)
                msg = json.loads(msg)  # return the msg as a dict
                print(msg)
            except Exception as e:
                print("Timeout: ", e)
                ack_msg = {
                    "type": MessageType.ACK.name,
                    "id": expection_seq,
                    "msg": "neg" + seq,
                    "checksum": checksum("neg" + seq)
                }
                ack_msg = json.dumps(ack_msg)
                UDPClientSocket.sendto(ack_msg.encode('UTF-8'), dest)
            if segment_counter == 0:
                filename = msg["filename"]
                file_size = int(msg["filesize"])
            check_sum = msg["checksum"]
            seq = msg["id"]
            data_as_bytes = base64.b64decode(msg["data"].encode('UTF-8'))  # recieve the data for the file
            seg_size = len(data_as_bytes)
            data_as_str = msg["data"]
            with open(filename, 'wb+') as file:
                # Packet lost test
                # if int(seq) == 40 and counter <= 2:
                #     ack_msg = {
                #         "type": MessageType.ACK.name,
                #         "id": seq,
                #         "msg": "neg" + seq,
                #         "checksum": checksum("ACK" + seq)
                #     }
                #     ack_msg = json.dumps(ack_msg)
                #     counter += 1
                #     UDPClientSocket.sendto(ack_msg.encode('UTF-8'), dest)
                if str(checksum(
                        data_as_str)) == check_sum:  # if the check sum is the same then send an ACK you recieved all the data
                    if seq not in segments_recv:
                        ack_msg = {
                            "type": MessageType.ACK.name,
                            "id": seq,
                            "msg": "ACK" + seq,
                            "checksum": checksum("ACK" + seq)
                        }
                        ack_msg = json.dumps(ack_msg)
                        UDPClientSocket.sendto(ack_msg.encode('UTF-8'), dest)
                        self.progress['value'] = ((total_recv_size + seg_size) / file_size) * 100
                        segments_recv[seq] = data_as_bytes
                        segment_counter += 1
                        total_recv_size = total_recv_size + seg_size
                        expection_seq += 1
                        test = total_recv_size - int(file_size)
                        if total_recv_size - int(file_size) >= 0:
                            for data in segments_recv.values():
                                file.write(data)  # write the data you recieved in the file you opened
                            self.proceed_flag=False
                            break
                    else:
                        continue
                else:
                    ack_msg = {
                        "type": MessageType.ACK.name,
                        "id": seq,
                        "msg": "neg" + seq,
                        "checksum": checksum("neg" + seq)
                    }
                    ack_msg = json.dumps(ack_msg)
                    UDPClientSocket.sendto(ack_msg.encode('UTF-8'), dest)
                # UDPClientSocket.sendto(msg,dest)

    def recieve_msg(self):
        self.Chat_log.config(state=NORMAL)  # Allow to change the chat log when a new msg arrive
        self.Chat_log.insert(END,
                             "Welcome to the Server! You can now chat\n")
        self.Chat_log.config(state=DISABLED)
        while True:
            try:  # Receive
                meg_recv = client_socket.recv(1024)
                meg_recv = json.loads(meg_recv)
                if not len(meg_recv):  # if you recieved an 0 length msg from the server
                    print("connection closed by server")
                    sys.exit()
                msg_type = meg_recv['type']
                if msg_type == MessageType.DOWNLOAD.name:
                    server_port = meg_recv['msg']
                    _thread.start_new_thread(self.download_file, (server_port,))

                else:
                    self.Chat_log.config(state=NORMAL)
                    self.Chat_log.insert(END,
                                         meg_recv['msg'] + "\n")
                    self.Chat_log.config(state=DISABLED)

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
                        "type": str(MessageType.Publicmsg.name),
                        "username": str(self.name),
                        "msg": str(self.msg)
                    }
                    send_msg = json.dumps(send_msg)
                    client_socket.send(send_msg.encode('UTF-8'))
            break

    def __init__(self):
        # Create a chat window
        self.Chat_Window = Tk()
        self.Chat_Window.withdraw()

        # login screen
        self.login = Toplevel()
        self.login.title("Login")
        self.login.resizable(width=False, height=False)
        self.login.configure(width=400, height=320)
        self.login.config(bg="#29C1D6")

        # create a Label to login screen and place it
        self.pls = Label(self.login, text="I&H\n  Please Enter your Username",
                         justify=CENTER, font="Arial 14 bold", bg="#29C1D6")
        self.pls.place(relheight=0.15, relx=0.2, rely=0.07)

        # create a Label to username and entry box to login screen
        self.labelName = Label(self.login, text="Username:",
                               bg="#29C1D6", font="Arial 13", justify=CENTER)
        self.labelName.place(relheight=0.2, relx=0.1, rely=0.2)

        self.username = Entry(self.login, bg="#C6DFE3", font="Arial 15", justify=CENTER)
        self.your_ip = Entry(self.login, bg="#C6DFE3", font="Arial 15", justify=CENTER)

        self.username.place(relwidth=0.3, relheight=0.10, relx=0.35, rely=0.23)
        self.your_ip.place(relwidth=0.3, relheight=0.10, relx=0.35, rely=0.6)
        self.login_button = Button(self.login, text="login", bg="#C6DFE3",
                                   font="Arial 15 bold", command=lambda: self.Login(self.username.get()))
        self.your_ip_Button = Button(self.login, text="enter your ip", bg="#C6DFE3",
                                   font="Arial 15 bold", command=lambda: self.change_ip(self.your_ip.get()))

        self.login_button.place(relx=0.4, rely=0.37)
        self.your_ip_Button.place(relx=0.33, rely=0.75)

        self.Chat_Window.mainloop()

    def change_ip(self,ip):
        self.server_ip = ip

    def Login(self, UserName):
        client_socket.connect((self.server_ip, port))
        user_connect = {
            "type": str(MessageType.CONNECT.name),
            "username": UserName,
        }
        user_connect = json.dumps(user_connect)
        client_socket.send(user_connect.encode('UTF-8'))
        self.login.destroy()
        self.ChatRoom_Gui(UserName)
        _thread.start_new_thread(self.recieve_msg, ())

    def ChatRoom_Gui(self, name):
        HeadFont = tkFont.Font(family="Arial", size=16, weight="bold", slant="italic")
        ChatFont = tkFont.Font(family="Arial", size=14)
        SendFont = tkFont.Font(family="Arial", size=10, weight="bold")
        self.Chat_Window.config(bg='#44BAEF')
        self.name = name
        self.Chat_Window.deiconify()
        self.Chat_Window.title("CHATROOM")
        self.Chat_Window.resizable(width=True,
                                   height=True)
        self.Chat_Window.geometry("800x600")

        self.top_label = Label(self.Chat_Window, bg='#44BAEF',
                               text="Ilan & Haim Chat                    "
                                    "                                "
                                    "        Username:" + self.name, font=HeadFont,
                               pady=9.5, anchor='w', )

        self.top_label.place(relwidth=1.2)

        self.Chat_log = Text(self.Chat_Window,width=20,height=2,bg='LightSkyBlue2',font=ChatFont,
                             padx=3,pady=3)

        self.Chat_log.place(relheight=0.650,relwidth=0.8,rely=0.08)

        self.labelBottom = Label(self.Chat_Window, bg='#44BAEF', height=110, width=80)

        self.file = Label(self.Chat_Window, bg='#44BAEF', text="File:", anchor=W, font=ChatFont, height=110, width=80)

        self.file.place(relwidth=1, relheight=0.08, rely=0.820)

        self.file_box = Entry(self.file, bg='light grey', font=ChatFont)

        self.progress = Progressbar(self.file, orient=HORIZONTAL, length=180, mode='determinate')

        self.progress.place(relheight=0.65, rely=0.100, relx=0.64)

        self.labelBottom.place(relwidth=1, relheight=0.08, rely=0.900)

        self.file_box.place(relwidth=0.30, relheight=0.8, rely=0.020, relx=0.08)

        self.Msg_box = Entry(self.labelBottom, bg='light grey', font=ChatFont)

        self.Msg_box.place(relwidth=0.74, relheight=0.9, rely=0.008, relx=0.004)

        self.Msg_box.focus()

        # create a Send Button
        self.buttonMsg = Button(self.labelBottom, text="Send", font=SendFont, width=20,
                                bg='SlateGray4', command=lambda: self.sendButton(self.Msg_box.get()))

        self.buttonMsg.place(relx=0.77, rely=0.008, relheight=0.7, relwidth=0.22)

        self.proceed_flag = False
        self.proceedButton = Button(self.file, text="proceed", font=SendFont,
                                    width=20, bg='SlateGray4', command=lambda: self.proceed_func())

        self.proceedButton.place(relx=0.87,rely=0.4,anchor=W,
                                 relheight=0.8,relwidth=0.12)

        self.file_button = Button(self.file,text="download",font=SendFont,
                                  width=20,bg='SlateGray4',
                                  command=lambda: self.download_Button(self.file_box.get()))

        self.file_button.place(relx=0.40,rely=0.40,anchor=W,
                               relheight=0.7,relwidth=0.22)

        # create option list to user-list and download-list
        self.user_option_label = Label(self.Chat_Window, bg='#44BAEF')
        self.user_option_label.pack(side=RIGHT)

        self.UserList = Button(self.user_option_label,text="User List",font=SendFont,
                               width=15,bg='SlateGray4',pady=10,
                               command=lambda: self.userList_serverList_button(0))

        self.UserList.pack(padx=3, pady=3)

        self.Server_files = Button(self.user_option_label,text="Show ServerFiles",
                                   font=SendFont,width=15,bg='SlateGray4',
                                   pady=10,command=lambda: self.userList_serverList_button(1))

        self.Server_files.pack(padx=3, pady=3)

        scrollbar = Scrollbar(self.Chat_log)
        scrollbar.pack(side=RIGHT, fill=Y)
        scrollbar.config(command=self.Chat_log.yview, bg='SlateGray4', activebackground='SlateGray4')

        self.Chat_log.config(state=DISABLED)


g = ChatGUI()
client_socket.close()
