import logging
import inspect
import typing
import logging
import asyncio
import json

class EventHandler:
    def __repr__(self):
        return "[EventHandler]"

    async def on_event(self, event: str, *args: typing.Any, **kwargs: typing.Dict[str, typing.Any]):
        if len(args) == 0:
             args_section = ""
        elif len(args) == 1:
            args_section = args[0]
        else:
            args_section = repr(args)
        kwargs_section = "" if not kwargs else repr(kwargs)
        logging.getLogger(__name__).debug(f"EVENT {event} {args_section} {kwargs_section}")

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

class MessageHandler(EventHandler):
    def __init__(self):
        self._msg_queue = asyncio.Queue()

    async def _handle_messages(self):
        while True:
            message = await self._msg_queue.get()
            asyncio.create_task(self._call_event("message", message))  
            self._msg_queue.task_done()

    async def _add_message(self, message):
        await self._msg_queue.put(message)
