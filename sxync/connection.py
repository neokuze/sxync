import asyncio
import base64
import random
import string
import traceback
import sys
import json
import aiohttp
from bs4 import BeautifulSoup

from . import room_events
from . import room as group
from .exceptions import InvalidRoom

import logging

class WS:
    def __init__(self, client):
        self._session = None
        self._ws = None
        self._client = client
        self._first_time = True
        self.url = "chat.roxvent.com"
        self._login_url = f'https://{self.url}/user/login/'
        self._ws_url = f'wss://{self.url}/ws/room/{self.name}/'
        self._room_url = f'https://{self.url}/room/{self.name}/'
        self._headers = {}
        self.logger = None

    @property
    def name(self):
        return self._name
    
    @property
    def client(self):
        return self._client

    async def listen_websocket(self):
        async with self._session as session:
            async with session.ws_connect(self._ws_url, headers=self.headers) as ws:
                if int(self.client.debug) <= 2:
                    logging.info(f"[info] {self.name} Websocket connection success!")
                asyncio.create_task(self.receive_messages(ws))
                while True:
                    try:
                        await asyncio.sleep(60)
                    except asyncio.CancelledError: break

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
                if int(self.client.debug) <= 2:
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
    
    async def _send_command(self, command):
        if self._ws and not self._ws.closed:
            await self._ws.send_json(command)

    async def close_session(self):
        if self._session:
            await self._session.close()

    def generate_header(self):
        key = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(16)).encode('utf-8')
        headers = {
            'Connection': 'keep-alive, Upgrade',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.5',
            'Origin': f'https://{self.url}',
            'Sec-WebSocket-Version': '13',
            'Sec-WebSocket-Extensions': 'permessage-deflate',
            'Sec-WebSocket-Key': base64.b64encode(key).decode('utf-8'),
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'websocket',
            'Sec-Fetch-Site': 'same-origin',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
            'Upgrade': 'websocket',
        }
        return headers
    
    async def _connect(self, anon=False):
        self.headers = self.generate_header()
        self.cookie_jar = aiohttp.CookieJar(unsafe=False)
        self._session = aiohttp.ClientSession(cookie_jar=self.cookie_jar, headers={'referer': self._login_url})

        response = await self._session.get(self._login_url)
        isvalid = None
        if response.status == 200:
            page_content = await response.text()
            soup = BeautifulSoup(page_content, 'html.parser')
            csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})['value']
            login_data = {
                'csrfmiddlewaretoken': csrf_token,
                'username': self._client._username,
                'password': self._client._password,
            }
            get_login = await self._session.post(self._login_url, data=login_data, headers={'referer': self._login_url})
            html_login = await get_login.text()
            soup = BeautifulSoup(html_login, 'html.parser')
            invalid_passwd = soup.find('ul', class_='messages')
            if not self._client._password: 
                ecode = 201
            if invalid_passwd is not None:
                invalid_passwd = invalid_passwd.find('li', class_='warning')
            if invalid_passwd:
                ecode = 202
            else:
                room_valid = await self._session.get(self._room_url, headers={'referer': self._login_url})
                soup = BeautifulSoup(await room_valid.text(), 'html.parser')
                isvalid = soup.find('button', {'class': 'btn btn-primary'})
                session_id_value = None
                for cookie in self._session.cookie_jar:
                    if cookie.key == 'sessionid':
                        session_id_value = cookie.value
                        break
                if session_id_value:
                    ecode = 200
                    self.headers['Cookie']=f"csrftoken={csrf_token}; sessionid={session_id_value}"
            
            if self._client.debug <= 1:    
                if ecode == 200: logging.info("[info] [ws] Login success...")
                if ecode == 201: logging.info("[info] [ws] Login as anon success...")
                if ecode == 202: logging.info("[info] [ws] Incorrect Password...")
            if isvalid == None:
                Tasks = [asyncio.create_task(self.listen_websocket())]
                asyncio.gather(*Tasks)
            else:
                await self._client.leave_room(self.name)
                raise InvalidRoom("The room doesn't exist.")
            