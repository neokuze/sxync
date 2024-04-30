from .connection import WS
from .utils import public_attributes

class PM(WS):
    def __init__(self, name, client):
        self._name = name
        self._client = client
        self._user = None
        self._type = 'pm'
        self.reset()
        super().__init__(client) # debe estar al final para cargar lo demas.

    def reset(self):
        self._history = []
        self._mqueue = {}
        self._friends = {}
 

    @property
    def type(self):
        return self._type


    def __dir__(self):
        return public_attributes(self)
    
    def __repr__(self):
        return "[pm: %s]"% self._name
        
    @property
    def name(self):
        return self._name     

    @property
    def user(self):
        return self._user

    async def init(self):
        await self._send_command({"cmd":"get_updates","kwargs":{"target":24}})
        await self._send_command({"cmd":"get_rooms","kwargs":{"target":24}})
        await self._send_command({"cmd":"get_recent","kwargs":{"target":24}})