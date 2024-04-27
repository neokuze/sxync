import asyncio
import typing
import inspect
import logging

from .room import Room
from .exceptions import AlreadyConnected, InvalidRoom
from .handler import EventHandler
from .utils import public_attributes, is_room_valid

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

    def _prune_tasks(self):
        self._tasks = [task for task in self._tasks if not task.done()]

    async def _task_loop(self, forever=False):
        while self._tasks or forever:
            await asyncio.gather(*self._tasks)
            self._prune_tasks()
            if forever:
                await asyncio.sleep(0.1)

    async def start(self):
        self._running = True
        tasks = [self.join_room(room_name) for room_name in self._rooms if room_name not in self._tasks]
        await asyncio.gather(*tasks)
        await self._task_loop(True)


    async def stop_all(self):
        for ws in list(self._tasks):
            self._tasks[ws]._listen_task.cancel()
            self._tasks[ws]._process_task.cancel()
            await self._tasks[ws].close_session()
        self._running = False
        
    async def join_room(self, room_name):
        if room_name in self._tasks:
            raise AlreadyConnected("User already connected. ")
        if not await is_room_valid(room_name):
            raise InvalidRoom("Invalid room.")
        room = self._tasks[room_name] = Room(room_name, self)
        await room._connect(anon=False)

    async def leave_room(self, room_name):
        room = self._tasks.get(room_name)
        if room != None:
            if self._tasks[room_name]._session:
                await self._tasks[room_name].close_session()
            del self._tasks[room_name]
            
