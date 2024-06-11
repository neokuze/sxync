
from .user import User


async def on_ok(data):
    self = data.get('self')
    self._name = data.get('target')
    self._user = User(data.get('target'))
    self._channel = None
    self._user_agent = data['you'].get('info')
    self._uid = data['you'].get('uid')
    await self.client._call_event("connect", self)


async def on_recent_rooms(data):
    """
{'self': [pm: 0], 'target': 24, 'recent': [
    {'id': 16, 'owner_id': 30, 'name': 'yadrier', 'title': 'SXYNC YADRIER', 'about': 'solo una sala de pruebas de yadrier un bot hecho con sxync un libreria en python', 'settings': {}, 'profile_image': None, 'banner_image': None, 'private': 1, 'left': '2024-06-09T22:30:04.135Z'}, 
    {'id': 17, 'owner_id': 30, 'name': 'sxync', 'title': 'POR NEOKUZE', 'about': '', 'settings': {}, 'profile_image': None, 'banner_image': None, 'private': 1, 'left': '2024-06-09T22:30:04.053Z'}, 
    {'id': 1, 'owner_id': 1, 'name': 'lootinggames', 'title': 'LootingGames', 'about': 'La wea fome de Milton', 'settings': {}, 'profile_image': '/media/images/user_1/thumb.webp', 'banner_image': '', 'private': 1, 'left': '2024-06-09T22:30:03.915Z'},
 {'id': 11, 'owner_id': 24, 'name': 'sudoers', 'title': 'Mi chat', 'about': 'Neokuze#7064', 'settings': {}, 'profile_image': None, 'banner_image': None, 'private': 1, 'left': '2024-06-09T22:30:03.804Z'}], 'owned': []}
    """
    self = data.get('self')
    # self._recent_rooms = data['kwargs']['recent']


async def on_unknown(data): pass
