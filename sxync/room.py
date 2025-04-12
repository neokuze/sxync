import html as html2
from collections import deque
from .connection import WS
from typing import List
from .utils import public_attributes
from .user import User
from .exceptions import UserNotFound
import asyncio
import time


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

    async def _delete_message(self, tid, delay: float=0.0):
        """
        Must be run in another task
        """
        async def delete():
            await asyncio.sleep(delay)
            message = self.get_message(tid)
            if message:
                await message.delete()
        self.client.add_task(delete())

    async def send_msg(self, text: str, html:bool=False, reply: int=0, delete_after: float=0.0):
        """
        Send message to the room.
        """
        msg = html2.unescape(text) if html else html2.escape(text)
        data = {"text": msg,"target":self.name, "tid": str(int(time.time() * 1000))}
        if reply: data.update({"a": int(reply)})
        await self._send_command({"cmd":"message","kwargs": data})
        if delete_after:
            await self._delete_message(data['tid'], delete_after)
            

    def get_user(self, username: str | User) -> User:
        if isinstance(username, User):
            username = username.showname

        if not isinstance(username, str):
            raise TypeError("argument must be str or User class.")
        exist = [x for x in self._userlist if x.showname.lower() == username.lower()]
        if exist:
            return exist[0]
        raise UserNotFound("User not found in room.")

    def get_recent(self, username: str | User):
        if isinstance(username, User):
            username = username.showname

        if not isinstance(username, str):
            raise TypeError("argument must be str or User class")
        exist = [x for x in self._userlist if x.showname.lower() == username.lower()]
        if exist:
            return self._userlist[exist[0]]
        raise UserNotFound("User not found in room.")

    @property
    def history(self):
        self._history = sorted(self._mqueue.items(), key=lambda x: x[0], reverse=True)
        return [msg for id, msg in self._history]
    
    def get_last_message(self, user_name: str | User):
        """
        Search message by username
        """
        if isinstance(username, User):
            username = username.showname

        if not isinstance(username, str):
            raise TypeError("argument must be str or User class")
            
        user = self.get_user(user_name)
        if user:
            user_messages = [msg for msg in self.history if msg.user.id == user.id]
            if user_messages:
                return user_messages[0]
            return False
        raise UserNotFound("User not found in room.")

    def get_message(self, tid: str):
        if tid:
            user_messages = [msg for msg in self.history if msg.tid == tid]
            if user_messages:
                return user_messages[0]
            return False
        return None

    def _filter_userlist(self, active: bool, anon: bool = None) -> List:
        if anon is not None:
            return [
                user for user, recents in self._userlist.items()
                if (recents.sessions if active else not recents.sessions) and 
                (user.isanon if anon is not None else True) == anon
            ]
        else: # should show inactive with both
            return [
                user for user, recents in self._userlist.items()
                if (recents.sessions if active else not recents.sessions) 
            ]

    def _alluserlist(self, _filter: str='all', active: bool=True) -> List:
        anon = None
        if _filter == 'anons':
            anon = True
        elif _filter == 'users':
            anon = False
        return self._filter_userlist(active, anon)

    @property
    def raw_userlist(self) -> List:
        """
        raw userlist (all connected and disconnected users.)
        """
        return self._userlist

    @property
    def alluserlist(self) -> List:
        """
        all userlist (all connected users.)
        """
        return self._alluserlist()

    @property
    def anonlist(self) -> List:
        """
        active anonlist (anons connected)
        """
        return self._alluserlist('anons')

    @property
    def userlist(self) -> List:
        """
        Active userlist (users connected)
        """
        return self._alluserlist('users')
    
    @property
    def recents(self) -> List:
        """
        only show recents, but only inactive users. not show at all.
        """
        return self._alluserlist('all', False)

    async def delete_user(self, username: str):
        user = self.get_user(username)
        await self._send_command({"cmd":"delete_user","kwargs":{"uid": user.id, "target":self.name}})

    async def clear_all(self):
        await self._send_command({"cmd":"delete_chat","kwargs":{"target":self.name}})

    def _is_bot(self, user: User):
        if user in self._userlist:
            return self._userlist[user].is_bot
        raise UserNotFound("User not found in room.")
        
    def _is_user(self, user: User):
        if user in self._userlist:
            return self._userlist[user].is_user
        raise UserNotFound("User not found in room.")

    async def _get_unban_list(self):
        await self._send_command({"cmd":"get_banlist","kwargs":{}})

    async def ban(self, username: str):
        user = self.get_user(username)
        if user is not None:
            await self._send_command({"cmd":"ban_user","kwargs":{"uid":user.id, "uip": ""}})
            
    async def unban(self, username: str):
        user = self.get_user(username)
        if user is not None:
            await self._send_command({"cmd":"unban_user","kwargs":{"uid":user.uid, "uip": ""}})
    

        
"""
'ban_user',{uid:uid,uip:uip}
('unban_user',{bid:banid})

"""