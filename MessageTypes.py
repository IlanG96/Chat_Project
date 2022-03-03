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

