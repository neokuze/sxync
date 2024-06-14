from .user import User
from .utils import public_attributes
import re

class Message(object):  # base
    def __init__(self):
        self._user = None
        self._room = None
        self._time = 0
        self._body = str()
        self._raw = str()
        self._ip   = str()
        self._device = str()

    def __dir__(self):
        return public_attributes(self)

    def __repr__(self):
        return "[Message]"

    @property
    def user(self):
        return self._user

    @property
    def room(self):
        return self._room

    @property
    def time(self):
        return self._time

    @property
    def body(self):
        return self._body

    @property
    def raw(self):
        return self._raw
    

class RoomBase(Message):
    def __init__(self):
        self._id = None
        self._mentions = list()
        self._edited = False
        
    @property
    def mentions(self):
        return self._mentions
    
    @property
    def edited(self):
        return self._edited

    
def mentions(body, room):
    t = []
    patron = r"([ \t\n\r\f\v])?@([a-zA-Z0-9áéíóúÁÉÍÓÚñÑ¿!?]{1,20})([ \t\n\r\f\v])?"
    for match in re.findall(patron, body):
        for participant in room.alluserlist:
            if participant.showname.lower() == match[1].lower():
                if participant not in t:
                    t.append(participant)
    return t
    
def _process_room_msg(mid, room, user_id, text, msg_time, raw = None, ip=None, dev=None):
    msg = RoomBase()
    if int(user_id) < 0 and raw:
        anon_name = "Anon"
        msg._user = User(int(user_id), name=anon_name.lower(), isanon=True, showname=anon_name)
    else:
        msg._user = User(int(user_id))
    msg._room = room
    msg._time = msg_time
    msg._raw = str(raw)
    msg._body = str(text)
    msg._mentions = mentions(msg._body, room)
    msg._id = mid
    msg._ip = ip
    msg._device = dev
    return msg
