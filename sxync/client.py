import asyncio
import typing
import inspect
import logging

from .room import Room
from .exceptions import AlreadyConnected
from .handler import EventHandler
from .utils import public_attributes

logger = logging.getLogger(__name__)

class Bot(EventHandler):
    def __init__(self, username, password, rooms=[]):
        self._username = username
        self._password = password
        self.debug = 1
        self._rooms = rooms
        self._tasks = {}
        self._running = None
    
    def __dir__(self):
        return public_attributes(self)
    
    @property
    def rooms(self):
        return list(self._tasks.keys())

    async def start(self):
        self._running = True
        for room_name in self._rooms:
            if room_name not in self._tasks:
                await self.join_room(room_name)
        while True:
            if not self._running:
                break
            await asyncio.sleep(0)  # Cede el control a otros eventos y tareas

    async def stop_all(self):
        for ws in list(self._tasks):
            await self._tasks[ws].close_session()
        self._running = False
        
    async def join_room(self, room_name):
        if room_name in self._tasks: 
            logger.error("User already connected.")
            return
        self._tasks[room_name] = Room(room_name, self)
        await asyncio.ensure_future(self._tasks[room_name]._connect(anon=False))

    async def leave_room(self, room_name):
        room = self._tasks.get(room_name)
        if room != None:
            if self._tasks[room_name]._session:
                await self._tasks[room_name].close_session()
            del self._tasks[room_name]
            
