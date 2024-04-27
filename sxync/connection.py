import asyncio
import base64
import random
import string
import traceback
import sys
import json
import aiohttp
import logging

from . import room_events
from . import room as group
from . import constants
from .exceptions import InvalidRoom
from . import utils
from .handler import RequestQueue

class WS:
    def __init__(self, client, max_workers=10):
        self._session = None
        self._ws = None
        self._client = client
        self._first_time = True
        self._listen_task = None
        self._recv_task = None
        self._headers = {}
        self.logger = None
        self._auto_reconnect = True
        self.queue = RequestQueue(self._session)

    @property
    def name(self):
        return self._name
    
    @property
    def client(self):
        return self._client
    
    async def _send_command(self, command):
        if self._ws and not self._ws.closed:
            await self._ws.send_json(command)

    async def close_session(self):
        if self._session:
            await self._session.close()
            
    async def listen_websocket(self):
        self._process_task = asyncio.create_task(self.queue.process())
        while self._auto_reconnect:
            self._ws = await self._session.ws_connect(constants.ws_url+f'{self.name}/', headers=self._headers)
            try:
                async for msg in self._ws:
                    assert msg.type is aiohttp.WSMsgType.TEXT
                    await self.queue.add_request(
                            (await self._receive_messages(msg))
                        )
            except (AssertionError,aiohttp.ClientError, asyncio.TimeoutError, ConnectionError, ConnectionResetError) as e:
                logging.error(f"Attempt to reconnect: {e}")
            except asyncio.CancelledError: 
                break
            if not self._auto_reconnect:
                break
            if self._auto_reconnect:
                await asyncio.sleep(5)

    async def _receive_messages(self, msg):
        async def process_cmd(msg):
            try:
                data = json.loads(msg.data)
                cmd = data.get('cmd')
                kwargs = data.get('kwargs') or {}
                kwargs = {'self': self} | kwargs  # python3.9 =>
                if self._first_time:
                    args = {'self': self}
                    await getattr(room_events, "on_connect")(args)
                    self._first_time = False
                if hasattr(room_events, f"on_{cmd}"):
                    try:
                        await getattr(room_events, f"on_{cmd}")(kwargs)
                    except:
                        logging.error("Error handling command: %s", cmd, exc_info=True)
                        traceback.print_exc(file=sys.stderr)
                else:
                    logging.warning("Unhandled received command", cmd, kwargs)
            except Exception as e:
                logging.warning("Unhandled exception in receive_messages", exc_info=True)
                traceback.print_exc(file=sys.stderr)
        await process_cmd(msg)

    async def _connect(self, anon=False):
        """
        function that supposed to connect.
        """
        if not self._session:
            self._session = utils.get_aiohttp_session()
        self.queue._session = self._session
        self._headers = utils.generate_header()
        if not anon:
            await self._login()
        if await utils.is_room_valid(self.name) == True:
            self._listen_task = await asyncio.create_task(self.listen_websocket())
        else:
            await self._client.leave_room(self.name)
            raise InvalidRoom("The room doesn't exist.")

    async def _login(self):
        login = await utils._fetch_html(constants.login_url, headers={})
        Jar = utils.Jar(login, self._client._username, self._client._password)
        await Jar.login_post()
        if Jar.success:
            self._headers['Cookie']=f"csrftoken={Jar.csrftoken}; sessionid={Jar.session_id_value}"
            return True
        return False    