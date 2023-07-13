from .user import User

class Message(object):  # base
    def __init__(self):
        self._user = None
        self._room = None
        self._time = 0
        self._body = str()
        self._raw = str()

    def __dir__(self):
        return [x for x in
                set(list(self.__dict__.keys()) + list(dir(type(self)))) if
                x[0] != '_']

    def __repr__(self):
        return "<Message>"

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
        self._tid = 0
        
    def quote(self, id=None):
        if not id: id = self._id
        return "[quote id={}/]".format(id)
    
def _process_room_msg(msg_id, room, user_id, text, msg_time, tid=None, raw = None):
    msg = RoomBase()
    msg._user = User(int(user_id))
    msg._room = room
    msg._time = msg_time
    msg._raw = str(raw)
    msg._body = str(text)
    msg._id = msg_id
    msg._tid = tid
    return msg
