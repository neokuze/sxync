
from .user import User

async def on_ok(data):
    self = data.get('self')
    self._name = data.get('target')
    self._user = User(data.get('target'))
    self._channel = None
    self._user_agent = data['you'].get('info')
    self._uid = data['you'].get('uid')

async def on_recent_rooms(data):
    self = data.get('self')
    # self._recent_rooms = data['kwargs']['recent']

async def on_unknown(data):pass

