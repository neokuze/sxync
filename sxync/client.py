import asyncio
import typing
import inspect
import logging

from typing import Coroutine, List, Union
from asyncio import Future, Task

from .room import Room
from .exceptions import AlreadyConnected, InvalidRoom
from .handler import EventHandler
from .utils import public_attributes, is_room_valid, Jar, _fetch_html
from . import constants

class Bot(EventHandler):
    def __init__(self, username, password, rooms=[], forever=True):
        self._username = username
        self._password = password
        self._Jar = Jar(username, password)
        self.debug = 1
        self._rooms = rooms
        self._watching_rooms = {}
        self._tasks: List[Task] = []
        self._task_loops: List[Task] = []
        self._running = None
        self._forever = forever
    
    def __repr__(self):
        return "[client]"

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

    async def start(self, *, forever=False):
        await self._call_event("init")
        login = await _fetch_html(constants.login_url, headers={})
        self._Jar.get(login)
        self.running = True
        for room_name in self._rooms:
            self.join_room(room_name)
        await self._call_event("start")
        await self._task_loop(self._forever)

    def stop_all(self):
        for ws in list(self._watching_rooms.keys()):
            room = self.get_room(ws)
            self.add_task(room.cancel())
        self._running = False
        
    def join_room(self, room_name) -> None:
        if room_name not in self._watching_rooms.keys():
            self.add_task(self._watch_room(room_name))

    async def _watch_room(self, room_name: str):
        if room_name in self._tasks:
            raise AlreadyConnected("User already connected. ")
        if not await is_room_valid(room_name):
            raise InvalidRoom("Invalid room.")
        room = self._watching_rooms[room_name] = Room(room_name, self)
        await room._connect(anon=False)

    def leave_room(self, room_name: str):
        room = self.get_room(room_name)
        if room:
            self.add_task(room.cancel())
            self._watching_rooms.pop(room_name)

    def add_task(self, coro_or_future: Union[Coroutine, Future]):# TODO
        task = asyncio.create_task(coro_or_future)
        self._handle_task_options(task)

    def _handle_task_options(self, task: Task):
        self._tasks.insert(0, task)
            
    def get_room(self, room_name: str):
        return self._watching_rooms.get(room_name)