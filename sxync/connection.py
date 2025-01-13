import asyncio
import base64
import random
import string
import traceback
import sys
import json
import aiohttp
import logging
from asyncio import TimeoutError

from typing import Optional

from . import room_events, pm_events
from . import room as group
from . import constants
from .exceptions import InvalidRoom, InvalidPasswd, WebSocketClosure
from . import utils

from aiohttp import ClientTimeout
from aiohttp.http_websocket import WSCloseCode, WebSocketError
from aiohttp.client_exceptions import ServerDisconnectedError, ServerTimeoutError

RTimeout = 5
TIMEOUT = 5


class WS:
    def __init__(self, client):
        self._client = client
        self.reconnect = False
        self._session = None
        self._ws = None
        self._listen_task = None
        self._headers = {}


    def __repr__(self):
        return "[ws: %s]" % self._name

    @property
    def name(self):
        return self._name

    @property
    def client(self):
        return self._client

    async def _send_command(self, command):
        if self._ws and not self._ws.closed:
            await self._ws.send_json(command)

    async def _close_connection(self):
        if self._ws:
            await self._ws.close()

    async def _close_session(self):
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
            
    async def _listen_websocket(self):
        timeout = ClientTimeout(sock_connect=300, sock_read=300)
        while self.reconnect:
            try:
                headers = {'referer': constants.login_url}
                headers.update(self._headers)
                self._session = aiohttp.ClientSession(headers=headers)
                peername = "wss://{}/ws/{}/{}/".format(
                    constants.url, self._type, self._name)
                self._ws = await self._session.ws_connect(peername, headers=headers, compress=15)
            except (aiohttp.client_exceptions.ClientConnectorError,
                aiohttp.client_exceptions.WSServerHandshakeError
                ) as e:
                logging.error("Websocket connection Error.")
            else:
                self.reset()
                try:
                    await self._init()
                    while True:  # / while for receiving data? do
                        if self._ws and not self._ws.closed:
                            msg = await asyncio.wait_for(self._ws.receive(), timeout=timeout.total)
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                await self._receive_message(msg.data)
                            elif msg.type is aiohttp.WSMsgType.ERROR:
                                logging.debug('Received error %s', msg)
                                raise WebSocketClosure
                            elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSING, aiohttp.WSMsgType.CLOSE):
                                logging.debug('Received %s', msg)
                                raise WebSocketClosure
                        else:
                            break
                except (ConnectionResetError, WebSocketClosure, asyncio.exceptions.CancelledError,
                        ServerDisconnectedError, WebSocketError
                        ) as e:
                    if isinstance(e, asyncio.CancelledError):
                        logging.debug("WebSocket listener task cancelled")
                        return # Interrupt loop
                    if self._ws and self._ws.closed:
                        errorname = {code: name for name,
                                    code in WSCloseCode.__members__.items()}
                        logging.error("[WS] {}: {}".format( self.name, errorname[self._ws.close_code]))
                        
                        if errorname[self._ws.close_code] in [WSCloseCode.SERVICE_RESTART, WSCloseCode.ABNORMAL_CLOSURE]:
                            await self._client._get_new_session()
                    
                except (asyncio.TimeoutError, ServerTimeoutError, TimeoutError):
                    await asyncio.sleep(TIMEOUT)
                
                finally:
                    await self._disconnect(False)
                    
                    

    async def _receive_message(self, msg):
        data = json.loads(msg)
        try:
            cmd = data.get('cmd')
            kwargs = data.get('kwargs') or {}
            kwargs.update({'self': self})
            
            events = room_events if self._type == 'room' else pm_events
            if hasattr(events, f"on_{cmd}"):
                try:
                    await getattr(events, f"on_{cmd}",)(kwargs)
                except:
                    logging.error("Error handling command: %s",
                                  cmd, exc_info=True)
                    traceback.print_exc(file=sys.stderr)
            else:
                print("Unhandled received command", cmd, kwargs)
                
        except Exception as e:
            logging.warning(
                "Unhandled exception in receive_messages", exc_info=True)
            traceback.print_exc(file=sys.stderr)

    async def _connect(self, anon=False):
        """
        function that supposed to connect.
        """
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession(headers=self._headers)

        room = {"GET": f"/ws/{self.type}/{self._name}/ HTTP/1.1"}
        self._headers = room | utils.generate_header()
        if not anon:
            if self.client._Jar.success is None:
                 await asyncio.shield(self._login()) 
            elif self.client._Jar.success:
                self._headers['Cookie'] = "csrftoken={}; sessionid={}".format(
                    self.client._Jar.csrftoken, self.client._Jar.session_id_value)

        # connect (?)
        self._listen_task = asyncio.create_task(self._listen_websocket())
        await self._connection_wait()
        
    async def _connection_wait(self):
        if self._listen_task:
            await self._listen_task

    def cancel(self):
        self.reconnect = False
        if self._listen_task and not self._listen_task.cancelled() and not self._listen_task.done():
            self._listen_task.cancel()

    async def _login(self):
        if self.client._password:
            await self.client._Jar.login_post()
            if self.client._Jar.success:
                self._headers['Cookie'] = "csrftoken={}; sessionid={}".format(
                    self.client._Jar.csrftoken, self.client._Jar.session_id_value)
            else:
                raise InvalidPasswd("Invalid Password")

    async def _disconnect(self, show=True):
        await self._close_connection()
        await self._close_session()
        if show:
            await self.client._call_event("disconnect", self)

    async def close(self):
        self.cancel()
        await self._disconnect()

    async def listen(self, anon=False, reconnect=True):
        """
        Join and wait on room connection
        """
        self.reconnect = reconnect
        while True:
            await self._connect(anon)
            if not self.reconnect:
                break
            await asyncio.sleep(3)

    async def disconnect(self, anon=False, reconnect=True):
        self.reconnect = False
        await self.close()
