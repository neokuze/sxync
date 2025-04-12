from .user import User
from .utils import public_attributes, remove_html_tags
import re

class Message(object):  # base
    def __init__(self):
        self._id = None
        self._user = None
        self._room = None
        self._time = 0
        self._body = str()
        self._raw = str()
        self._ip   = str()
        self._device = str()
        self._tid = str()
        self._delete_after = int()

    def __dir__(self):
        return public_attributes(self)

    def __repr__(self):
        return "[Message]"

    @property
    def id(self):
        return self._id

    @property
    def tid(self):
        return self._tid

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
        self._mentions = list()
        self._edited = False
        self._old = ""
        self._replied = 0
 
    @property
    def mentions(self):
        return self._mentions
    
    @property
    def edited(self):
        return self._edited
    
    @property
    def replied(self):
        return self._replied

    @property
    def old(self):
        return None if not self._old else self._old
    
    async def edit(self, text):
        """
        {"cmd":"edit_message","kwargs":{"msgid": self._id,"text":"boba","target": self._room}}
        """
        await self._room._send_command({"cmd":"edit_message","kwargs":{"msgid": self.id,"text": text,"target": self._room._name}})
        
    async def flag(self):
        await self._room._send_command({"cmd": "flag_message","kwargs": {"uid":self.user.id, "msgid": self.id}})
    
    async def delete(self):
        await self._room._send_command({"cmd":"delete_message","kwargs":{"target":self._room._name,"msgid":self.id}})

    
def mentions(body, room):
    t = []
    patron = r"([ \t\n\r\f\v])?@([a-zA-Z0-9áéíóúÁÉÍÓÚñÑ¿!?]{1,20})([ \t\n\r\f\v])?"
    for match in re.findall(patron, body):
        for participant in room.alluserlist:
            if participant.showname.lower() == match[1].lower():
                if participant not in t:
                    t.append(participant)
    return t
    
def _process_room_msg(mid, room, user_id, text, _time:str = "", tid:str = "", raw = None, ip=None, dev=None, replied=0):
    msg = RoomBase()
    if int(user_id) < 0 and raw:
        anon_name = "Anon"
        msg._user = User(int(user_id), name=anon_name.lower(), isanon=True, showname=anon_name)
    else:
        msg._user = User(int(user_id))
    msg._room = room
    msg._time = _time
    msg._raw = str(raw)
    msg._body = remove_html_tags(text)[1:]
    msg._mentions = mentions(msg._body, room)
    msg._tid = str(tid)
    msg._id = mid
    msg._ip = ip
    msg._device = dev
    msg._replied = replied
    return msg

def _process_edited(room, msgid, text):
    old_body = room._mqueue[int(msgid)]._body
    room._mqueue[int(msgid)]._old = old_body
    room._mqueue[int(msgid)]._body = str(text)
    room._mqueue[int(msgid)]._mentions = mentions(text, room)
    room._mqueue[int(msgid)]._edited = True
    return room._mqueue[int(msgid)]


def button(text: str, name: str):
    b = f"""<button onclick="room_mounted.current_connection.sendToSocket('message',{{'text':'{text}'}})">{name}</button>"""
    return b
