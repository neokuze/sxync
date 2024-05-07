import aiohttp
from collections import deque
from .utils import cleanText, public_attributes, get_aiohttp_session
from . import constants

class User: 
    _users = {}

    def __new__(cls, userid, **kwargs):
        key = f"user_{userid}"
        anonymous=False
        if "-" in str(userid):
            key = "Anon"+str(userid)[1:]
            anonymous=True
        if key in cls._users:
            for attr, val in kwargs.items():
                setattr(cls._users[key], '_' + attr, val)
            return cls._users[key]
        self = super().__new__(cls)
        self._name = None
        self._key = key
        self._id = int(f"{userid}")
        cls._users[key] = self
        self._name = None if not anonymous else key
        self._history = deque(maxlen=5)
        self._isanon = anonymous
        self._showname = None
        self._client = None
        self._last_time = None
        self._banner = None
        self._profile_img = None
        self._ip = None
        self._dev = None
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
        return "[user: %s]" % self.name
    
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
    
    async def get_data(self):
        url = f"https://chat.roxvent.com/user/API/get_data/?id={self.id}"
        async with get_aiohttp_session().get(url, headers={'referer': constants.login_url}) as resp:
            data = await resp.json()
            result = data.get('reason')
            if result == "PROFILE FOUND":
                result = data.get('profile')
                self._name = cleanText(result['custom'])
                self._showname = result['custom']
                self._banner = result['banner']
                self._profile_img = result['image']
                