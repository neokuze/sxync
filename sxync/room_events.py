import asyncio

from .message import _process_room_msg
from .user import User

async def on_update_user_counter(data):
    self = data.get('self')
    self._usercounter = data.get('number')
    
async def on_message(data):
    msg_id =   data.get('id')
    self = data.get('self') # cliente. duh
    user_id = data.get('user_id') #l a base de datos nos guarda por id
    text = data.get('text') # Body
    msg_time = data.get('time') # Tiempo del mensaje
    tid =  data.get('tid') # algun tiempo de actividad.
    msg = _process_room_msg(msg_id, self, user_id, text, msg_time, tid, data)
    self._mqueue[int(msg_id)] = msg
    await self.client._call_event("message", msg)
    
async def on_userlist(data):
    self = data.get('self') # cliente. duh
    self._userlist.clear()
    ul = data.get('userlist')
    for person in ul:
        active = person.get('active')
        _time = person.get('time')
        target = User(person.get('user_id'))
        _from = User(data.get('user_id'))
        self._userlist[target] = {
            'from': _from,
            'user_id': target,
            'active': int(active),
            'time' : _time.split('.',1)[0],
            'left_time': 0}
        t = [ _from.get_data(self._session), target.get_data(self._session)]
        asyncio.gather(*t)
    
async def on_join_user(data):
    self = data.get('self') # cliente. duh
    user = User(data.get('user_id'))
    active = data.get('active')
    _time = data.get('time')
    if not user._name and data.get('user_id') >=1: 
        await user.get_data(self._session)
    if user not in self._userlist:
        self._userlist[user] = {'active':1, 'time': _time,'left_time': 0}
    else:
        self._userlist[user]['active'] = active
    await self._client._call_event("join_user", self, user, _time)
    
async def on_disconnect_user(data):
    self = data.get('self') # cliente. duh
    user = User(data.get('user_id'))
    active = data.get('active')
    _time = data.get('time')
    left_time = data.get('left_time')
    if user in self._userlist:
        self._userlist[user]['active'] = active
        self._userlist[user]['left_time'] = left_time
        self._userlist[user]['time'] = _time
    await self._client._call_event("leave_user", self, user, left_time)
    
    
async def on_history(data):
    mlist = data.get('messages')
    self = data.get('self')
    mlist = mlist[1:]
    for value in mlist:
        msg_id = value[0]
        user = value[1]
        text = value[2]
        _time = value[3]
        msg = _process_room_msg(msg_id, self, user, text, _time)
        self._mqueue[int(msg_id)] = msg
        

async def on_writing(data):pass
