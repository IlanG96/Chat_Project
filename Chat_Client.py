import json
import socket
import select
import errno
import sys
import threading as thread
from tkinter import *
import tkinter.font as tkFont
from enum import Enum


class MessageType(Enum):
    CONNECT = 'connect'
    USERSLIST = 'get_users'
    DISCONNECT = 'disconnect'
    Privatemsg = 'set_msg'
    Publicmsg = 'set_msg_all'
    GETLISTFILE = 'get_list_file'
    DOWNLOAD = 'download'
    PROCEED = 'proceed'


client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
port = 55000
client_socket.connect(('127.0.0.1', port))




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
                            rely=0.2)

        # set the focus of the cursor
        # self.username.focus()

        # create a Continue Button
        # along with action
        self.go = Button(self.login,
                         text="CONTINUE",
                         font="Arial 15 bold",
                         command=lambda: self.Login(self.username.get()))

        self.go.place(relx=0.4,
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
        self.name = name
        # to show chat window
        self.Chat_Window.deiconify()
        self.Chat_Window.title("CHATROOM")
        self.Chat_Window.resizable(width=True,
                                   height=True)
        # self.Chat_Window.configure(width=600,
        #                            height=800,
        #                            bg="#6173A4")
        self.Chat_Window.geometry("800x600")
        self.labelHead = Label(self.Chat_Window,
                               bg="#9DA7C5",
                               text="Username:" + self.name,
                               font=HeadFont,
                               pady=3)

        self.labelHead.place(relwidth=1)
        self.line = Label(self.Chat_Window,
                          width=450,
                          bg="#ABB2B9")

        self.line.place(relwidth=1,
                        rely=0.07,
                        relheight=0.012)

        self.Chat_log = Text(self.Chat_Window,
                             width=20,
                             height=2,
                             bg="#6173A4",
                             font=ChatFont,
                             padx=3,
                             pady=3)

        self.Chat_log.place(relheight=0.745,
                            relwidth=1,
                            rely=0.08)

        self.labelBottom = Label(self.Chat_Window,
                                 bg="#ABB2B9",
                                 height=80)

        self.labelBottom.place(relwidth=1,
                               rely=0.825)

        self.Msg_box = Entry(self.labelBottom,
                             bg="#6173A4",
                             font=ChatFont)

        # place the given widget
        # into the gui window
        self.Msg_box.place(relwidth=0.74,
                           relheight=0.06,
                           rely=0.008,
                           relx=0.011)

        self.Msg_box.focus()

        # create a Send Button
        self.buttonMsg = Button(self.labelBottom,
                                text="Send",
                                font=SendFont,
                                width=20,
                                bg="#ABB2B9",
                                command=lambda: self.sendButton(self.Msg_box.get()))

        self.buttonMsg.place(relx=0.77,
                             rely=0.008,
                             relheight=0.06,
                             relwidth=0.22)

        self.UserList = Button(self.Chat_Window,
                               text="User List",
                               font=SendFont,
                               width=15,
                               bg="#ABB2B9",
                               pady=10,
                               command=lambda: self.user_list_button())
        self.UserList.pack(anchor="w", side="bottom")
        self.Server_files = Button(self.Chat_Window,
                               text="Show server files",
                               font=SendFont,
                               width=15,
                               bg="#ABB2B9",
                               pady=10,
                               command=lambda: self.user_list_button())
        self.Server_files.pack(side=BOTTOM)
        #self.UserList.pack(side=BOTTOM)
        # create a scroll bar
        scrollbar = Scrollbar(self.Chat_log)

        # place the scroll bar
        # into the gui window
        scrollbar.place(relheight=1,
                        relx=0.974)

        scrollbar.config(command=self.Chat_log.yview)

        self.Chat_log.config(state=DISABLED)

    def user_list_button(self):
        # If the user list button is pressed send a Userlist msg request
        self.msg = MessageType.USERSLIST.name
        send_thread = thread.Thread(target=self.send_msg)
        send_thread.start()

    # function to basically start the thread for sending messages
    def sendButton(self, msg):
        # get a msg that was entered in the text box and send her
        self.Chat_log.config(state=DISABLED) # prevent typing in the chat log.
        self.msg = str(msg)
        self.Msg_box.delete(0, END)
        send_thread = thread.Thread(target=self.send_msg)
        send_thread.start()

    def recieve_msg(self):
        self.Chat_log.config(state=NORMAL) # Allow to change the chat log when a new msg arrive
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
                if msg_type == MessageType.CONNECT.name:
                    self.Chat_log.config(state=NORMAL)
                    self.Chat_log.insert(END,
                                         meg_recv['msg'] + "\n")
                    self.Chat_log.config(state=DISABLED)
                elif msg_type == MessageType.Publicmsg.name or msg_type == MessageType.Privatemsg.name or msg_type == MessageType.USERSLIST.name:
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
                if self.msg.startswith('@PM['): # Check if its a PM
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
                elif self.msg == MessageType.USERSLIST.name: # Check if its a User_list request
                    User_req = {
                        "type": str(MessageType.USERSLIST.name)
                    }
                    PM_msg = json.dumps(User_req)
                    client_socket.send(PM_msg.encode('UTF-8'))
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

