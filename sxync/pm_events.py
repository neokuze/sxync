
from .user import User

async def on_ok(data):
    self = data.get('self')
    self._name = data.get('target')
    self._user = User(data.get('target'))
