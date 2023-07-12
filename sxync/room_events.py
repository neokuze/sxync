import asyncio

from .message import RoomBase
from .user import User

async def on_update_user_counter(data):
    self = data.get('self')
    self._usercounter = data.get('number')
    
async def on_message(data):
    self = data.get('self') # cliente. duh
    room = self
    text = data.get('text') # Body
    tid =  data.get('tid') # algun tiempo de actividad.
    user_id = data.get('user_id') #l a base de datos nos guarda por id
    msg_time = data.get('time') # Tiempo del mensaje
    msg_id =   data.get('id')
    msg = RoomBase()
    msg._user = User(int(user_id))
    msg._room = room
    msg._time = msg_time
    msg._raw = str(data)
    msg._body = str(text)
    msg._id = msg_id
    msg._tid = tid
    await self.client._call_event("message", msg)
    
async def on_userlist(data):
    self = data.get('self') # cliente. duh
    room = self
    room._userlist.clear()
    ul = data.get('userlist')
    for person in ul:
        active = person.get('active')
        _time = person.get('time')
        target = User(person.get('user_id'))
        _from = User(data.get('user_id'))
        room._userlist[target] = {
            'from': _from,
            'user_id': target,
            'active': int(active),
            'time' : _time.split('.',1)[0],
            'left_time': 0}
        t = [ _from.get_data(self._session), target.get_data(self._session)]
        asyncio.gather(*t)
    
async def on_join_user(data):
    self = data.get('self') # cliente. duh
    room = self
    user = User(data.get('user_id'))
    active = data.get('active')
    _time = data.get('time')
    if not user._name and data.get('user_id') >=1: 
        await user.get_data(self._session)
    if user not in room._userlist:
        room._userlist[user] = {'active':1, 'time': _time,'left_time': 0}
    else:
        room._userlist[user]['active'] = active
    await self._client._call_event("join_user", room, user, _time)
    
async def on_disconnect_user(data):
    self = data.get('self') # cliente. duh
    room = self
    user = User(data.get('user_id'))
    active = data.get('active')
    _time = data.get('time')
    left_time = data.get('left_time')
    if user in room._userlist:
        room._userlist[user]['active'] = active
        room._userlist[user]['left_time'] = left_time
        room._userlist[user]['time'] = _time
        
    await self._client._call_event("leave_user", room, user, left_time)
    
    
async def on_history(data):pass

async def on_writing(data):pass
