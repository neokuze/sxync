import asyncio
from datetime import datetime, timezone

from .message import _process_room_msg, _process_edited
from .user import User, Recents
from .utils import Struct
from .flags import RoomFlags


async def on_writing(data): pass


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
    await self._user.get_data()
    await self.client._call_event("connect", self)


async def on_message(data):  # TODO
    self = data.get('self')  # cliente. duh
    user_id = data.get('uid')  # l a base de datos nos guarda por id
    text = data.get('text')  # Body
    msg_time = data.get('time')  # Tiempo del mensaje
    mid = data.get('mid')  # algun tiempo de actividad.
    ip = data.get('uip')
    dev = data.get('dev')
    msg = _process_room_msg(mid, self, user_id, text, msg_time, data, ip, dev)
    self._mqueue[int(mid)] = msg
    if len(self._mqueue) > self._limit:
        oldest_mid = sorted(self._mqueue.keys())[0]
        del self._mqueue[oldest_mid]
    await self.client._call_event("message", msg)
    


async def on_userlist(data):
    """
    proper use of userlist
    """
    self = data.get('self')
    ul = data.get('userlist')
    users = []
    for user_data in ul:
        user = User(user_data.get('uid'))
        users.append(user)
        sessions = user_data.get('active')
        info = user_data.get('device')
        join_time = user_data.get('join').split('.')[0]
        self._userlist[user] = Recents(
            {'sessions': sessions, 'join_time': join_time, 'info': dict(device=info)})
    if 'count' in data:
        self._usercounter = data.get('count')
    if users:
        get_all_profiles = [user.get_data() for user in users]
        asyncio.gather(*get_all_profiles)


async def on_join(data):
    """
    {'uid': 30, 'sessions': 1, 'usercount': 3, 'join': '2024-03-14T01:23:59.549Z'}

    """
    self = data.get('self')
    user = User(data.get('uid'))
    active = data.get('sessions')
    join_time = data.get('join').split('.')[0]
    info = data.get('info', {})
    if user not in self._userlist:
        self._userlist[user] = Recents(
            dict(sessions=active, join_time=join_time, info=info))
    else:
        self._userlist[user]._update(
            dict(sessions=active, join_time=join_time, info=info))
    if not user._fetched_profile and not user.isanon:
        fetch = [user.get_data(), asyncio.sleep(0)]
        asyncio.gather(*fetch)
    await self.client._call_event("join_user", self, user, join_time)


async def on_leave(data):
    """
    {'uid': 1, 'sessions': 0, 'usercount': 3}
    """
    self = data.get('self')
    user = User(data.get('uid'))
    usercount = data.get('usercount')
    now = datetime.now(timezone.utc)
    iso_format = now.replace(microsecond=0).isoformat().split('+')[0].split('.')[0]
    if user in self._userlist:
        info = dict(left_time=iso_format)
        info.update(data)
        self._userlist[user]._update(info)
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
    msg = self._mqueue[int(msgid)]
    result = True if data.get('result') == "OK" else False
    if result:  # eliminar de mi vista
        del self._mqueue[int(msgid)]
    await self.client._call_event("message_deleted", msg, result)


async def on_permissions(data):
    """
    'BANEABLE': True, 'IS_MOD': False, 'IS_OWNER': 0, 'DELETE_MESSAGES': 0, 'DELETE_OWN_MESSAGES': 0, 
    'DUMMY': 0, 'DELETE_ALL_MESSAGES': 0, 'EDIT_OWN_MESSAGES': 0, 'ROOM_INFO': 0, 'ROOM_SETTINGS': 0,
    'ROOM_RESTRICTIONS': 0, 'FLAG_USER': 0, 'SEE_IPS': 0, 'BAN_USERS': 0, 'UNBAN_USERS': 0, 'ADD_MOD': 0, 'CHANGE_MODS': 0, 'flag': 0})
    """
    self = data.get('self')
    permissions_data = {k: v for k, v in data.items() if k != 'self'}
    self._permissions = RoomFlags(permissions_data)


async def on_recent_users(data): #TODO
    """ 
    'recent': [{'uid': -181, 'info': {'device': 'Mobile'}, 'join_time': '2024-05-29T19:53:42.512Z', 'left_time': '2024-05-29T19:58:17.540Z', 'ip': ''},
    """
    self = data.get('self')
    recent = data.get('recent')
    if recent:
        userlist = []
        for obj in recent:
            user = User(obj.get('uid'))
            if user not in self._userlist:
                self._userlist[user] = Recents(obj)
            else:
                self._userlist[user]._update(obj)
            userlist.append(user)
        if userlist:
            get_all_profiles = [user.get_data() for user in userlist]
            asyncio.gather(*get_all_profiles)
            

async def on_edit_message(data):
    """
    ('result': 'OK', 'msgid': 53206, 'text': 'morning o.o/', 'target': ''})
    """
    self = data.get('self')
    result = data.get('result')
    msgid = data.get('msgid')
    text = data.get('text')
    msg = self._mqueue[int(msgid)]
    if msgid in self._mqueue and result == "OK":
        msg = _process_edited(self, msgid, text)
    await self.client._call_event("message_edited", msg, result)

async def on_delete_chat(data):
    self = data.get("self")
    ok = data.get("result")
    user = User(data.get('uid'))
    result = True if ok == "OK" else False
    await self.client._call_event("clear", self, user, result)

async def on_rejected(data):
    self = data.get('self')
    print(f"{self.name} | rejected connection.")
    
async def wrong_command(data):
    print(f"Wrong command {self.name}: ",data)



