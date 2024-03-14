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

from bs4 import BeautifulSoup

cookie_jar = aiohttp.CookieJar(unsafe=False)

class WS:
    def __init__(self, client):
        self._session = None
        self._ws = None
        self._client = client
        self._first_time = True
        self._listen_task = None
        self._recv_task = None
        self._headers = {}
        self.logger = None

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
        async with self._session as session:
            async with session.ws_connect(constants.ws_url+f'{self.name}/', headers=self._headers) as ws:
                if int(self.client.debug) <= 2:
                    logging.info(f"[info] {self.name} Websocket connection success!")
                self._recv_task = await asyncio.create_task(self.receive_messages(ws))
                while True:
                    try:
                        await asyncio.sleep(0) # give control to async
                    except asyncio.CancelledError: break
                    except ConnectionResetError: pass

    async def receive_messages(self, ws):
        self._ws = ws
        while True:
            try:
                msg = await ws.receive()
                assert msg.type is aiohttp.WSMsgType.TEXT
                await self._process_cmd(msg.data)
            except AssertionError: pass
            except asyncio.CancelledError: break
            except ConnectionResetError:
                logging.info(f"[info] {self.name} Websocket connection was reset.")

    async def _process_cmd(self, data):
        data = json.loads(data)
        cmd = data.get('cmd')
        kwargs = data.get('kwargs') or {}
        kwargs = {'self': self} | kwargs  # python3.9
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
    
    async def _connect(self, anon=False):
        """
        function that supposed to connect.
        """
        if not self._session:
            self._headers = utils.generate_header()
            self._session = aiohttp.ClientSession(cookie_jar=cookie_jar, headers={'referer': constants.login_url})
        if not self._is_cookie_valid():
            login, token = await self._login()
            ecode = await self._parse_data(login, token)
            if ecode == 200: logging.info("[info] [ws] Login success...")
            if ecode == 201: logging.info("[info] [ws] Login as anon success...")
            if ecode == 202: logging.info("[info] [ws] Incorrect Password...")
        if await utils.is_room_valid(self._session, self.name) == True:
            self._listen_task = await asyncio.create_task(self.listen_websocket())
        else:
            await self._client.leave_room(self.name)
            raise InvalidRoom("The room doesn't exist.")

    async def _parse_data(self, data, token):
        """
        supposed to parse data
        """
        soup = BeautifulSoup(data, 'html.parser')
        invalid_passwd = soup.find('ul', class_='messages')
        if not self._client._password: 
            ecode = 201
        if invalid_passwd is not None:
            invalid_passwd = invalid_passwd.find('li', class_='warning')
        if invalid_passwd:
            ecode = 202
        else:
            session_id_value = None
            for cookie in self._session.cookie_jar:
                if cookie.key == 'sessionid':
                    session_id_value = cookie.value
                    break
            if session_id_value:
                ecode = 200
                self._headers['Cookie']=f"csrftoken={token}; sessionid={session_id_value}"
        return ecode

    async def _login(self, username: str = "", password: str = ""):
        """
        a fuction that can login, or maybe. 
        """
        response = await self._session.get(constants.login_url)
        if response.status == 200:
            page_content = await response.text()
            soup = BeautifulSoup(page_content, 'html.parser')
            csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})['value']
            login_data = {
                'csrfmiddlewaretoken': csrf_token,
                'username': username or self._client._username,
                'password': password or self._client._password,
            }
            get_login = await self._session.post(constants.login_url, data=login_data, headers={'referer': constants.login_url})
            login = await get_login.text()
            return (login, csrf_token)
    
    def _is_cookie_valid(self):
        for cookie in cookie_jar:
            if cookie.key == 'sessionid':
                return True
        return False
    