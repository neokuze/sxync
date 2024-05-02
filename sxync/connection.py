import asyncio
import base64
import random
import string
import traceback
import sys
import json
import aiohttp
import logging

from . import room_events, pm_events
from . import room as group
from . import constants
from .exceptions import InvalidRoom, InvalidPasswd, WebSocketClosure
from . import utils

from aiohttp import ClientTimeout
from aiohttp.http_websocket import WSCloseCode, WebSocketError
from aiohttp.client_exceptions import ServerDisconnectedError, ServerTimeoutError

class WS:
    def __init__(self, client, max_workers=10):
        self._session = None
        self._ws = None
        self._client = client
        self._listen_task = None
        self._headers = {}
        self.logger = None
        self._auto_reconnect = None
        self._transport = None


    def __repr__(self):
        return "[ws: %s]"% self._name
    @property
    def name(self):
        return self._name
    
    @property
    def client(self):
        return self._client

    async def _send_command(self, command):
        await self._ws.send_json(command)

    def _close_session(self):
        if self._ws:
            self._ws.close()
    
    async def _listen_websocket(self):
        self._auto_reconnect = True
        while self._auto_reconnect:
            try:
                self._session = aiohttp.ClientSession()
                peername = "wss://{}/ws/{}/{}/".format(constants.url, self._type, self.name)
                self._ws = await self._session.ws_connect(peername, headers=self._headers, autoping=True, autoclose=True)
            except aiohttp.ClientConnectionError as e:
                logging.error(f"Error al conectar al WebSocket: {e}")
                return
            self.reset(); await self._init() #/ make sure of getting data every time it connected
            try:
                timeout = ClientTimeout(sock_connect=300,sock_read=300)
                while True: # / while for receiving data? do
                    if self._session.closed:
                        raise ServerDisconnectedError #/ reconect (?)
                    msg = await asyncio.wait_for(self._ws.receive(), timeout=timeout.total)
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        await self._receive_message(msg.data)
                    elif msg.type is aiohttp.WSMsgType.ERROR:
                        logging.debug('Received error %s', msg)
                        raise WebSocketClosure
                    elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSING, aiohttp.WSMsgType.CLOSE):
                        logging.debug('Received %s', msg)
                        raise WebSocketClosure
            except (ConnectionResetError, ServerTimeoutError, WebSocketClosure,
                    ServerDisconnectedError, WebSocketError, asyncio.exceptions.CancelledError) as e:
                if isinstance(e, asyncio.CancelledError):
                    logging.debug("WebSocket listener task cancelled")
                    break
                if self._ws and self._ws.closed:
                    errorname = {code: name for name, code in WSCloseCode.__members__.items()}
                    logging.error("[WS] {}: {}".format(self.name, errorname[self._ws.close_code]))
                    break
            finally:
                if self._auto_reconnect:
                    await asyncio.sleep(5)

        await self.disconnect(reconnect=self._auto_reconnect)
        await self._client._call_event("disconnect", self)

    async def _receive_message(self, msg):
        data = json.loads(msg)
        try:
            cmd = data.get('cmd')
            kwargs = data.get('kwargs') or {}
            kwargs = {'self': self} | kwargs  # python3.9 =>
            events = room_events if self._type == 'room' else pm_events
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

    async def _connect(self, anon=False):
        """
        function that supposed to connect.
        """
        if not self._session:
            self._session = utils.get_aiohttp_session()
        room = {"GET": f"/ws/{self.type}/{self.name}/ HTTP/1.1"}
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
        if self._listen_task and not self._listen_task.cancelled() and not self._listen_task.done():
            self._listen_task.cancel()


    async def disconnect(self, reconnect=None):
        self._close_session()
        if reconnect:
            await self._connect()
            self._client._call_event("reconnect", self)
