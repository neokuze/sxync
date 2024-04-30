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
from .exceptions import InvalidRoom, InvalidPasswd, WebSocketClosure
from . import utils

from aiohttp.http_websocket import WSCloseCode

class WS:
    def __init__(self, client, max_workers=10, _type="room"):
        self._session = None
        self._ws = None
        self._client = client
        self._first_time = True
        self._listen_task = None
        self._process_task = None
        self._headers = {}
        self.logger = None
        self._auto_reconnect = None
        self._transport = None
        self._type = _type

    @property
    def name(self):
        return self._name
    
    @property
    def client(self):
        return self._client

    async def _send_command(self, command):
        await self._ws.send_json(command)

    async def _close_session(self):
        if self._ws:
            await self._ws.close()
    
    async def _listen_websocket(self):
        self._auto_reconnect = True
        while self._auto_reconnect:
            try:
                self._session = aiohttp.ClientSession()
                peername = "wss://{}/ws/{}/{}/".format(constants.url, self._type, self.name)
                self._ws = await self._session.ws_connect(peername, headers=self._headers, autoping=True, autoclose=True)
            except Exception as e:
                logging.error(f"Error al conectar al WebSocket: {e}")
                return
            try:
                while True: # / while for receiving data.
                    msg = await self._ws.receive(timeout=60.0)
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        await self._receive_message(json.loads(msg.data))
                    elif msg.type is aiohttp.WSMsgType.ERROR:
                        logging.debug('Received error %s', msg)
                        raise WebSocketClosure
                    elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSING, aiohttp.WSMsgType.CLOSE):
                        logging.debug('Received %s', msg)
                        raise WebSocketClosure
            except (ConnectionResetError, asyncio.TimeoutError, WebSocketClosure) as e:
                if self._ws and self._ws.closed:
                    errorname = {code: name for name, code in WSCloseCode.__members__.items()}
                    logging.error("[WS] {}: {}".format(self.name, errorname[self._ws.close_code]))
                if self._auto_reconnect:
                    await self.disconnect(reconnect=True)
                    break
                if self._auto_reconnect:
                    await asyncio.sleep(5)

    async def _receive_message(self, msg):
        async def process_cmd(msg):
            try:
                cmd = msg.get('cmd')
                kwargs = msg.get('kwargs') or {}
                kwargs = {'self': self} | kwargs  # python3.9 =>
                events = room_events if self._type == 'room' else None
                if self._first_time:
                    args = {'self': self}
                    self._first_time = False
                    await getattr(events, f"on_connect",)(args)
                if hasattr(events, f"on_{cmd}"):
                    try:
                        await getattr(events, f"on_{cmd}",)(kwargs)
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
        room = {"GET": f"/ws/room/{self.name}/ HTTP/1.1"}
        self._headers = room | utils.generate_header()
        if not anon:
            if self.client._Jar.success == None: await self._login()
            elif self.client._Jar.success == True:
                self._headers['Cookie']=f"csrftoken={self.client._Jar.csrftoken}; sessionid={self.client._Jar.session_id_value}"
        # connect (?)
        self._listen_task = asyncio.create_task(self._listen_websocket())
        await self._listen_task

    async def _login(self):
        if self.client._password:
            await self.client._Jar.login_post()
            if self.client._Jar.success:
                self._headers['Cookie']=f"csrftoken={self.client._Jar.csrftoken}; sessionid={self.client._Jar.session_id_value}"
            else:
                raise InvalidPasswd("Invalid Password")

    def cancel(self):
        self._auto_reconnect = False
        self._listen_task.cancel()

    async def disconnect(self, reconnect=None):
        self.cancel()
        await self._close_session()
        if reconnect:
            await self._connect()