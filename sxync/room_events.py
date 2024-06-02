import asyncio

from .message import _process_room_msg
from .user import User, Recents 
from .utils import Struct

from .flags import RoomFlags

async def on_writing(data):pass

async def on_ok(data):
    """
    proper use of room data.
    """
    self = data.get('self')
    me = data.get('you')
    client_info = me.get('info')
    chn = data.get('channel')
    self._user = User(me.get('uid'))
    self._info = Struct("ClientInfo", **dict(channel=chn, client=client_info))
    await self.client._call_event("connect", self)

async def on_update_user_counter(data): #TODO maybe change
    self = data.get('self')
    self._usercounter = data.get('number')

async def on_message(data): # TODO
    self = data.get('self') # cliente. duh
    user_id = data.get('uid') #l a base de datos nos guarda por id
    text = data.get('text') # Body
    msg_time = data.get('time') # Tiempo del mensaje
    mid =  data.get('mid') # algun tiempo de actividad.
    ip =  data.get('uip') 
    dev =  data.get('dev') 
    msg = _process_room_msg(mid, self, user_id, text, msg_time, data, ip, dev)
    self._mqueue[int(mid)] = msg
    await self.client._call_event("message", msg)
    if len(self._mqueue) > self._limit:
        oldest_mid = sorted(self._mqueue.keys())[0]
        del self._mqueue[oldest_mid]

async def on_userlist(data):
    """
    proper use of userlist
    """
    self = data.get('self') 
    self._userlist.clear()
    ul = data.get('userlist')
    for user_data in ul:
        user = User(user_data.get('uid'))
        sessions = user_data.get('active')
        join_time = user_data.get('join')
        self._userlist[user] = Recents({'sessions': sessions, 'join_time':join_time})
        t = [ user.get_data(), asyncio.sleep(0)]
        asyncio.gather(*t)
    if 'count' in data: self._usercounter = data.get('count')

async def on_join(data):
    """
    {'uid': 30, 'sessions': 1, 'usercount': 3, 'join': '2024-03-14T01:23:59.549Z'}

    """
    self = data.get('self')
    user = User(data.get('uid'))
    active = data.get('sessions')
    join_time = data.get('join')
    if not user._name and data.get('uid') >=1: 
        await user.get_data()
    if user not in self._userlist:
        self._userlist[user] = Recents({'sessions':1, 'join_time': join_time})
    else:
        self._userlist[user]._update(dict(join_time=join_time, sessions=active))
    await self.client._call_event("join_user", self, user, join_time)

async def on_leave(data):
    """
    {'uid': 1, 'sessions': 0, 'usercount': 3}
    """
    self = data.get('self') 
    user = User(data.get('uid'))
    sessions = data.get('sessions')
    usercount = data.get('usercount')
    if user in self._userlist:
        self._userlist[user]._update(data)
    self._usercounter = usercount
    await self.client._call_event("leave_user", self, user)

async def on_history(data):
    mlist = data.get('messages')
    self = data.get('self')
    if mlist:
        mlist = mlist[1:]
        for value in mlist:
            msg_id = value[0]
            user = value[1]
            text = value[2]
            _time = value[3]
            msg = _process_room_msg(msg_id, self, user, text, _time)
            self._mqueue[int(msg_id)] = msg

async def on_delete_message(data):
    self = data.get('self')
    msgid = data.get('msgid')
    if data.get('result') == "OK": #eliminar de mi vista
        del self._mqueue[int(msgid)]

async def on_permissions(data):
    """
    'BANEABLE': True, 'IS_MOD': False, 'IS_OWNER': 0, 'DELETE_MESSAGES': 0, 'DELETE_OWN_MESSAGES': 0, 
    'DUMMY': 0, 'DELETE_ALL_MESSAGES': 0, 'EDIT_OWN_MESSAGES': 0, 'ROOM_INFO': 0, 'ROOM_SETTINGS': 0,
    'ROOM_RESTRICTIONS': 0, 'FLAG_USER': 0, 'SEE_IPS': 0, 'BAN_USERS': 0, 'UNBAN_USERS': 0, 'ADD_MOD': 0, 'CHANGE_MODS': 0, 'flag': 0})
    """
    self = data.get('self')
    permissions_data = {k: v for k, v in data.items() if k != 'self'}
    self._permissions = RoomFlags(permissions_data)

async def on_recent_users(data):
    """
    'recent': [{'uid': -181, 'info': {'device': 'Mobile'}, 'join_time': '2024-05-29T19:53:42.512Z', 'left_time': '2024-05-29T19:58:17.540Z', 'ip': ''},
    """
    self = data.get('self')
    recent = data.get('recent')
    print(self, data)
    if recent:
        for obj in recent:
            user = User(obj.get('uid'))
            if user not in self._userlist:
                self._userlist[user] = Recents(obj)
            else:
                self._userlist[user]._update(obj)
