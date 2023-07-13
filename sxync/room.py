from collections import deque
from .connection import WS
from .utils import cleanText

class Room(WS):
    def __init__(self, name, client, anon=False):
        self._name = name
        self._client = client
        self._usercounter = 0
        self._users = {}
        self._anons = []
        self._history = []
        self._mqueue = {}
        self._userlist = {}
        self._log_as_anon = anon
        super().__init__(client) # debe estar al final para cargar lo demas.
        
    @property
    def name(self):
        return self._name
    
    async def on_connect(self):
        await self._send_command({"command":"get_userlist","kwargs":{"target":self.name}})
        await self._send_command({"command":"get_history","kwargs":{"target":self.name}})
        await self._client._call_event("connect", self)
        
    async def send_msg(self, text, quote=None):
        msg = text if quote == None else f"{quote}{text}"
        await self._send_command({"command":"message","kwargs":{"text":msg,"target":self.name}})
        
    def find_user_by_id(self, args):
        return [(x.id,x.name) for x in self._userlist if x.id == int(args)]
    
    def find_user_by_name(self, args):
        return [x.id for x in self._userlist if x.name.lower() == args.lower()]
    
    @property
    def history(self):
        self._history = sorted(self._mqueue.items(), key=lambda x: x[0], reverse=True)
        return [msg for id, msg in self._history]
    
    def get_last_message(self, user_name: str):
        clean_user = self.find_user_by_name(user_name)
        print(clean_user)
        user_messages = [msg for msg in self.history if msg.user.id == clean_user[0]]
        if user_messages:
            return user_messages[0]
        else:
            return None

    
class RoomFlags:
    pass