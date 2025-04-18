from .connection import WS
from .utils import public_attributes
from .user import User

class PM(WS):
    def __init__(self, client):
        self._name = "pm"
        self._client = client
        self._user = None
        self._type = 'pm'
        self._limit = 500
        self._channel = None
        self._user_agent = None
        self._uid = int()
        self.reset()
        super().__init__(client)  # debe estar al final para cargar lo demas.

    def reset(self):
        self._history = []
        self._mqueue = {}
        self._friends = {}
        self._recent_rooms = []

    @property
    def type(self):
        return self._type

    def __dir__(self):
        return public_attributes(self)

    def __repr__(self):
        return "[%s: %s]" % (self.__class__.__name__,self._uid)

    @property
    def name(self):
        return "PM: %s" % self.user.showname

    @property
    def user(self):
        return self._user

    async def _init(self):
        await self._send_command({"cmd": "get_updates", "kwargs": {"target": self._uid}})
        await self._send_command({"cmd": "get_rooms", "kwargs": {"target": self._uid}})
        await self._send_command({"cmd": "get_recent", "kwargs": {"target": self._uid}})
