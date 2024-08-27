import aiohttp
import json
import logging
from collections import deque
from .utils import cleanText, public_attributes
from . import constants

class User: 
    _users = {}

    def __new__(cls, userid, **kwargs):
        key = f"user_{userid}"
        anonymous=False
        if "-" in str(userid):
            key = "Anon"+str(userid)
            anonymous=True
        if key in cls._users:
            for attr, val in kwargs.items():
                setattr(cls._users[key], '_' + attr, val)
            return cls._users[key]
        self = super().__new__(cls)
        self._key = key
        self._id = int(f"{userid}")
        cls._users[key] = self
        self._name = key
        self._history = deque(maxlen=5)
        self._isanon = anonymous
        self._showname = None or key.replace('-', ' ')
        self._client = None
        self._last_time = None
        self._banner = None
        self._profile_img = None
        self._fetched_profile = False
        for attr, val in kwargs.items():
            setattr(self, '_' + attr, val)
        return self

    def get(name):
        if type(name) == type(int(0)):
            name = f"user_{name}"
        return User._users.get(name) or User(name)

    def __dir__(self):
        return public_attributes(self)

    def __repr__(self):
        return "[user: %s]" % self.showname

    @property
    def id(self):
        return int(self._id)

    @property
    def showname(self):
        return self._showname

    @property
    def name(self):
        return self._name

    @property
    def isanon(self):
        return self._isanon

    @property
    def picture(self):
        if self.id > 0:
            return "{}{}".format(constants.url, self._profile_img)
        return None

    async def get_data(self):
        if self.id > 0:
            url = constants.users_api+f"{self.id}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers={'referer': constants.login_url}) as resp:
                    content = await resp.text()
                    data = json.loads(content)
                    result = data.get('reason')
                    if result == "PROFILE FOUND":
                        result = data.get('profile')
                        self._name = cleanText(result['custom'])
                        self._showname = result['custom']
                        self._banner = result['banner']
                        self._profile_img = result['image']
                        self._fetched_profile = True

class Recents:
    def __init__(self, data):
        self._device = data.get('info', {}).get('device', '')
        self._join_time = data['join_time'].split('.')[0] if 'join_time' in data else None
        self._left_time = data['left_time'].split('.')[0] if 'left_time' in data else None
        self._sessions = data.get('sessions', None)
        self._ip = data.get('ip', None)

    def _update(self, data):
        if 'info' in data and data['info']:
            self._device = data['info'].get('device', "")
        if 'join_time' in data:
            self._join_time = data['join_time'].split('.')[0]
        if 'left_time' in data:
            self._left_time = data['left_time'].split('.')[0]
        if 'sessions' in data:
            self._sessions = data['sessions']
        if 'ip' in data:
            self._ip = data['ip']

    def __dir__(self):
        return public_attributes(self)

    def __repr__(self):
        return f"<{self.__class__.__name__}>"

    @property
    def device(self):
        return self._device

    @property
    def join_time(self):
        return self._join_time

    @property
    def left_time(self):
        return self._left_time

    @property
    def sessions(self):
        return self._sessions

    @property
    def ip(self):
        return self._ip

    @property
    def is_bot(self):
        return self._device.lower() == "bot"

    @property
    def is_mobile(self):
        return self._device.lower() == "mobile"

    @property
    def is_pc(self):
        return self._device.lower() == "pc"

    @property
    def is_user(self):
        return self._device.lower() in ["pc","mobile"]
