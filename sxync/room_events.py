import asyncio

from .message import _process_room_msg
from .user import User

async def on_ok(data):
    """
    proper use of room data.
    """
    self = data.get('self')
    user_info = data.get('you')
    ip_nmethod = user_info.get('info')
    ip, _, user_agent = ip_nmethod.split(";;")
    chn = data.get('channel')
    self._user = User(user_info.get('uid'))
    self._misc = dict(ip=ip,user_agent=user_agent,channel=chn)
    
async def on_connect(data):
    self = data.get('self')
    await self._send_command({"cmd":"get_userlist","kwargs":{"target":self.name}})
    await self._send_command({"cmd":"get_history","kwargs":{"target":self.name}})
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
    
async def on_userlist(data):
    """
    proper use of userlist
    """
    self = data.get('self') 
    self._userlist.clear()
    ul = data.get('userlist')
    for user_data in ul:
        user = User(user_data.get('uid'))
        sessions_active = user_data.get('active')
        join_time = user_data.get('join')
        t = [ user.get_data(self._session), asyncio.sleep(0)]
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
        await user.get_data(self._session)
    if user not in self._userlist:
        self._userlist[user] = {'sessions':1, 'time': join_time}
    else:
        self._userlist[user]['sessions'] = active
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
        self._userlist[user]['sessions'] = sessions
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
        

async def on_writing(data):pass
