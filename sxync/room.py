from collections import deque
from .connection import WS

class Room(WS):
    def __init__(self, name, client, anon=False):
        self._name = name
        self._client = client
        self._usercounter = 0
        self._users = {}
        self._history = deque(maxlen=400)
        self._anons = []
        self._userlist = {}
        self._log_as_anon = anon
        super().__init__(client) # debe estar al final para cargar lo demas.

        
    @property
    def name(self):
        return self._name
    
    async def on_connect(self):
        await self._ws.send_json({"command":"get_userlist","kwargs":{"target":self.name}})
        await self._ws.send_json({"command":"get_history","kwargs":{"target":self.name}})
        await self._client._call_event("connect", self)
        
    async def send_msg(self, text):
        await self._ws.send_json({"command":"message","kwargs":{"text":text,"target":self.name}})
        
    def find_user_by_id(self, args):
        return [(x.id,x.name) for x in self._userlist if x.id == int(args)]
    
    def find_user_by_name(self, args):
        return [(x.id,x.name) for x in self._userlist if x.name.lower() == int(args.lower())]
    
    
class RoomFlags:
    pass