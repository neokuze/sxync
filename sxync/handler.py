import logging
import inspect
import typing
import asyncio
import json
from concurrent.futures import ProcessPoolExecutor

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
        self._max_workers = 4
        self._executor = None
        self._semaphore = None

    def _get_executor(self):
        if self._executor is None:
            self._executor = ProcessPoolExecutor(max_workers=self._max_workers)
        return self._executor

    async def _handle_messages(self):
        """
        Consume messages from the queue and dispatch them concurrently.
        Uses a semaphore to limit concurrent message handlers.
        """
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self._max_workers * 2)

        while True:
            message = await self._msg_queue.get()
            await self._semaphore.acquire()
            task = asyncio.create_task(self._dispatch_message(message))
            task.add_done_callback(lambda t: self._semaphore.release())
            self._msg_queue.task_done()

    async def _dispatch_message(self, message):
        """
        Dispatch a single message event. Override-friendly for subclasses.
        """
        try:
            await self._call_event("message", message)
        except Exception as e:
            logging.getLogger(__name__).error(f"Error handling message: {e}", exc_info=True)

    async def run_in_process(self, func, *args):
        """
        Run a CPU-bound function in a separate process.
        Use this inside on_message handlers for heavy computation.
        
        Example:
            result = await self.run_in_process(heavy_function, arg1, arg2)
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._get_executor(), func, *args)

    async def _add_message(self, message):
        await self._msg_queue.put(message)

    def shutdown_executor(self):
        """Cleanup the process pool executor."""
        if self._executor:
            self._executor.shutdown(wait=False)
            self._executor = None
