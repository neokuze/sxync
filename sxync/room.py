import html as html2
from collections import deque
from .connection import WS
from typing import List
from .utils import cleanText, public_attributes

class Room(WS):
    def __init__(self, name, client, anon=False):
        self._name = name
        self._client = client
        self._type = 'room'
        self._limit = 1000
        self._log_as_anon = anon
        self._user = None
        self.reset()
        super().__init__(client) # debe estar al final para cargar lo demas.

    def reset(self):
        self._info = str()
        self._usercounter = 0
        self._history = []
        self._mqueue = {}
        self._userlist = {}   

    @property
    def type(self):
        return self._type

    def __dir__(self):
        return public_attributes(self)
    
    def __repr__(self):
        return "[room: %s]"% self._name
        
    @property
    def name(self):
        return self._name     

    @property
    def user(self):
        return self._user

    @property
    def info(self):
        return self._info

    async def _init(self):
        await self._send_command({"cmd":"get_userlist","kwargs":{"target":self.name}})
        await self._send_command({"cmd":"get_history","kwargs":{"target":self.name}})
        
    async def send_msg(self, text, html=False):
        msg = html2.unescape(text) if html else html2.escape(text)
        await self._send_command({"cmd":"message","kwargs":{"text": msg,"target":self.name}})
        
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
        user_messages = [msg for msg in self.history if msg.user.id == clean_user[0]]
        if user_messages:
            return user_messages[0]
        else:
            return None

    def _get_active_userlist(self) -> List:
        return [x for x in self._userlist if self._userlist[x]['sessions']]

    def _get_inactive_userlist(self) -> List:
        return [x for x in self._userlist if not self._userlist[x]['sessions']]

    def alluserlist(self, _filter: str='all', active: bool=True) -> List:
        if active:
            if _filter == 'anons':
                return [x for x in self._get_active_userlist() if x.isanon]
            elif _filter == 'users': 
                return [x for x in self._get_active_userlist() if not x.isanon]
            else:
                return [x for x in self._get_active_userlist()]
        else:
            if _filter == 'anons':
                return [x for x in self._get_inactive_userlist() if x.isanon]
            elif _filter == 'users': 
                return [x for x in self._get_inactive_userlist() if not x.isanon]
            else:
                return [x for x in self._get_inactive_userlist()]

    def get_user_sessions(self, user:str = "", by = "id") -> List:
        if by == "id":
            return [x for x in self._userlist.items() if x[0].id == int(user)]
        if by == "name":
            return [x for x in self._userlist.items() if x[0].name.lower() == user.lower()]
        else:
            return [x for x in self._userlist.items()]

    @property
    def anonlist(self) -> List:
        return self.alluserlist('anons')

    @property
    def userlist(self) -> List:
        return self.alluserlist('users')
        

class RoomFlags:
    pass