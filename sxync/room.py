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
        self._permissions = object()
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
    def permissions(self):
        return self._permissions

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

    def _filter_userlist(self, active: bool, anon: bool = None) -> List:
        return [
            user for user, recents in self._userlist.items()
            if (recents.sessions if active else not recents.sessions) and 
               (user.isanon if anon is not None else True) == anon
        ]

    def alluserlist(self, _filter: str='all', active: bool=True) -> List:
        if _filter == 'all':
            return [x for x in self._userlist]
        anon = None
        if _filter == 'anons':
            anon = True
        elif _filter == 'users':
            anon = False
        return self._filter_userlist(active, anon)

    @property
    def anonlist(self) -> List:
        return self.alluserlist('anons')

    @property
    def userlist(self) -> List:
        return self.alluserlist('users')
    