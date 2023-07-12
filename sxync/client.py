import asyncio
import typing
import inspect

from .room import Room
 
class Bot:
    def __init__(self, username, password, rooms=[]):
        self._username = username
        self._password = password
        self.debug = 1
        self._rooms = rooms
        self._tasks = {}
        self._running = None
        
    @property
    def rooms(self):
        return list(self._tasks.keys())

    async def start(self):
        for room_name in self._rooms:
            if room_name not in self._tasks:
                await self.join_room(room_name)
        while True:
            if not self._running:
                break
            self._running = True
            await asyncio.sleep(0)  # Cede el control a otros eventos y tareas

    async def stop_all(self):
        for ws in list(self._tasks):
            await self._tasks[ws].close_session()
        self._running = False
        
    async def join_room(self, room_name):
        if room_name not in self._tasks:
            self._tasks[room_name] = Room(room_name, self)
            await asyncio.ensure_future(self._tasks[room_name]._connect(anon=False))

    async def leave_room(self, room_name):
        room = self._tasks.get(room_name)
        if room != None:
            await self._tasks[room_name].close_session()

    async def on_event(self, event: str, *args: typing.Any, **kwargs: typing.Dict[str, typing.Any]):
        """print(event, repr(args), repr(kwargs))"""

    async def _call_event(self, event: str, *args, **kwargs):
        attr = f"on_{event}"
        await self.on_event(event, *args, **kwargs)
        if hasattr(self, attr):
            await getattr(self, attr)(*args, **kwargs)

    def event(self, func, name=None):
        assert inspect.iscoroutinefunction(func)
        if name is None:
            event_name = func.__name__
        else:
            event_name = name
        setattr(self, event_name, func)
    

