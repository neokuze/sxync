import aiohttp
from collections import deque

class User: 
    _users = {}

    def __new__(cls, userid, **kwargs):
        if type(userid) == type(int(0)):
            key = f"user_{userid}"
        if key in cls._users:
            for attr, val in kwargs.items():
                setattr(cls._users[key], '_' + attr, val)
            return cls._users[key]
        self = super().__new__(cls)
        self._name = None
        self._key = key
        self._id = int(f"{userid}")
        cls._users[key] = self
        self._name = None
        self._history = deque(maxlen=5)
        self._isanon = False
        self._showname = None
        self._client = None
        self._last_time = None
        self._banner = None
        self._profile_img = None
        for attr, val in kwargs.items():
            setattr(self, '_' + attr, val)
        return self
    
    def get(name):
        if type(name) == type(int(0)):
            name = f"user_{name}"
        return User._users.get(name) or User(name)

    def __dir__(self):
        return [x for x in
                set(list(self.__dict__.keys()) + list(dir(type(self)))) if
                x[0] != '_']

    def __repr__(self):
        return "<User: %s>" % self.name
    
    @property
    def id(self):
        return int(self._id)
    
    @property
    def showname(self):
        return self._showname
    
    @property
    def name(self):
        return self._name
    
    async def get_data(self, session):
        lurl = "https://chat.roxvent.com/user/login/"
        url = f"https://chat.roxvent.com/user/API/get_data/?id={self.id}"
        async with session.get(url, headers={'referer': lurl}) as resp:
            data = await resp.json()
            result = data.get('reason')
            if result == "PROFILE FOUND":
                result = data.get('profile')
                self._name = result['custom']
                self._banner = result['banner']
                self._profile_img = result['image']
                