import aiohttp
import json
import logging
from collections import deque
from .utils import public_attributes
from .exceptions import AnonMissingPicture
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
    def id(self) -> int:
        return int(self._id)

    @property
    def showname(self) -> str:
        return self._showname

    @property
    def mention(self) -> str:
        return "@"+self._showname

    @property
    def name(self) -> str:
        return self._name

    @property
    def isanon(self) -> bool:
        return self._isanon

    @property
    def picture(self) -> str:
        if self.id > 0:
            return "https://{}{}?v=1.jpg".format(constants.url, self._profile_img)
        raise AnonMissingPicture("Anon users doesn't have profile photo.")

    @property
    def gif(self) -> str:
        if self.id > 0:
            return "https://{}{}?v=1.gif".format(constants.url, self._profile_img)
        raise AnonMissingPicture("Anon users doesn't have profile photo.")

    async def get_data(self) -> None:
        if self.id > 0:
            url = constants.users_api+f"{self.id}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers={'referer': constants.login_url}) as resp:
                    content = await resp.text()
                    data = json.loads(content)
                    result = data.get('reason')
                    if result == "PROFILE FOUND":
                        result = data.get('profile')
                        self._name = result['custom']
                        self._showname = result['custom']
                        self._banner = result['banner']
                        self._profile_img = result['image']
                        self._fetched_profile = True
                        return None
                    return False

class Recents:
    def __init__(self, data):
        self._device = data.get('info', {}).get('device', '')
        self._join_time = data['join_time'].split('.')[0] if 'join_time' in data else ""
        self._left_time = data['left_time'].split('.')[0] if 'left_time' in data else ""
        self._sessions = data.get('sessions', 0)
        self._ip = data.get('ip', "")

    @property
    def all(self):
        return dict(device=self.device, join_time=self.join_time, left_time=self.left_time, 
            sessions=self.sessions, ip=self.ip, is_bot=self.is_bot,is_user=self.is_user,     
            is_pc=self.is_pc, is_mobile=self.is_mobile)

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
    def device(self) -> str:
        return self._device

    @property
    def join_time(self) -> str:
        return self._join_time

    @property
    def left_time(self) -> str:
        return self._left_time

    @property
    def sessions(self) -> int:
        return self._sessions

    @property
    def ip(self) -> str:
        return self._ip

    @property
    def is_bot(self) -> bool:
        return self._device.lower() == "bot"

    @property
    def is_mobile(self) -> bool:
        return self._device.lower() == "mobile"

    @property
    def is_pc(self) -> bool:
        return self._device.lower() == "pc"

    @property
    def is_user(self) -> bool:
        return self._device.lower() in ["pc","mobile"]
