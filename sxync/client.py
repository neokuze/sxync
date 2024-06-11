import asyncio
import typing
import inspect
import logging
import time

import aiohttp
from typing import Coroutine, List, Union
from asyncio import Future, Task

from . import constants
from .exceptions import AlreadyConnected, InvalidRoom
from .handler import EventHandler
from .utils import public_attributes, is_room_valid, Jar
from .room import Room
from .private_messaging import PM

class Bot(EventHandler):
    def __init__(self, username, password, rooms=[], forever=True):
        self._username = username
        self._password = password
        self.pm = None
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
        return list(self._watching_rooms.keys())

    def _prune_tasks(self):
        self._tasks = [task for task in self._tasks if not task.done()]

    async def _task_loop(self, forever=False):
        while self._tasks or forever:
            await asyncio.gather(*self._tasks)
            self._prune_tasks()
            if forever:
                await asyncio.sleep(0.1)

    async def start(self, *, forever=False, pm=True):
        await self._call_event("init")
        await self._get_new_session()
        self.running = True
        if pm:
            self.join_pm()
        for room_name in self._rooms:
            self.join_room(room_name)
        await self._call_event("start")
        await self._task_loop(self._forever)

    async def stop_all(self):
        for room_name in self.rooms:
            await self._watching_rooms[room_name].close()
            self._watching_rooms.pop(room_name)

        if self.pm:
            await self.pm.close()

        await self._Jar.aiohttp_session.close()
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
            self.add_task(room.close())
            self._watching_rooms.pop(room_name)

    def add_task(self, coro_or_future: Union[Coroutine, Future]):  # TODO
        task = asyncio.create_task(coro_or_future)
        self._handle_task(task)

    def _handle_task(self, task: Task):
        self._tasks.insert(0, task)

    def get_room(self, room_name: str):
        return self._watching_rooms.get(room_name)

    def join_pm(self):
        if not self._username or not self._password:
            logging.error("PM requires username and password.")
            return

        self.add_task(self._watch_pm())

    async def _watch_pm(self):
        pm = PM(self)
        self.pm = pm
        await pm._connect()

    def leave_pm(self):
        if self.pm:
            self.add_task(self.pm.close())

    async def _get_new_session(self):
        if self._Jar._counter <= time.time():
            self._Jar._counter = time.time() + self._Jar._limit
            while True:
                session = await self._Jar.get_new_session()
                if session:
                    break
