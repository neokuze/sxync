import logging
import inspect
import typing
import asyncio

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

class EventHandler:
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

class RequestQueue:
    def __init__(self, session, max_workers=10):
        self.queue = asyncio.Queue()
        self._session = session
        self._max_workers = max_workers
        self._workers = 0
        self._event = asyncio.Event()
        self._lock = asyncio.Lock()

    async def get(self):
        async with self._lock:
            self._workers += 1
            if self._workers >= self._max_workers:
                self._event.clear()
            request = await self.queue.get()
            return request

    async def add_request(self, request):
        await self.queue.put(request)
        if not self._event.is_set():
            self._event.set()

    async def process(self):
        while True:
            await self._event.wait()
            async with self._lock:
                request = None
                try:
                    request = await self.get()
                    print(f"Processing request: {request}")
                    await request(self._session)
                except Exception as e:
                    print(f"Error processing request: {e}")
                finally:
                    if request:
                        self.queue.task_done()
                    self._workers -= 1
                    if self._workers < self._max_workers:
                        self._event.set()

    async def close(self):
        async with self._lock:
            self._event.set()
