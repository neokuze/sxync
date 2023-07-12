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

    @property
    def name(self):
        return self._name
    
    @property
    def client(self):
        return self._client

    async def listen_websocket(self):
        self._ws = await self._session.ws_connect(self._ws_url, headers=self.headers)
        while True:
            try:
                msg = await self._ws.receive()
                if self._first_time:
                    await self.on_connect()
                    self._first_time = False
                try:
                    assert msg.type is aiohttp.WSMsgType.TEXT
                    data = json.loads(msg.data)
                    cmd = data.get('command')
                    kwargs = data.get('kwargs') or {}
                    kwargs = {'self': self} | kwargs  # python3.9 
                    if hasattr(room_events, f"on_{cmd}"):
                        try:
                            await getattr(room_events, f"on_{cmd}")(kwargs)
                        except asyncio.CancelledError:
                            break
                        except:
                            if int(self.client.debug) == 2:
                                print("Error manejando el comando:", cmd, file=sys.stderr)
                                traceback.print_exc(file=sys.stderr)
                    elif int(self.client.debug) == 2:
                        print("Comando no manejado: ", cmd, kwargs, file=sys.stderr)
                except AssertionError: pass
            except ConnectionResetError: pass
                    

    async def _connect(self, anon=False):
        key = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(16)).encode('utf-8')
        headers = {
            'Host': f'{self.url}',
            'Connection': 'keep-alive, Upgrade',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.5735.199 Safari/537.36',
            'Upgrade': 'websocket',
            'Sec-WebSocket-Version': '13',
            'Sec-WebSocket-Extensions': 'permessage-deflate',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.5',
            'Sec-WebSocket-Key': base64.b64encode(key).decode('utf-8')
        }
        cookie_jar=aiohttp.CookieJar(unsafe=False)
        self._session =  aiohttp.ClientSession(cookie_jar=cookie_jar, headers={'referer': self._login_url})
        response = await self._session.get(self._login_url)
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
                valid_room = await self._session.get(self._room_url, headers={'referer': self._login_url})
                isvalid = True
                if valid_room.status in [301,302,303]:
                    isvalid = False
                session_id_value = None
                for cookie in self._session.cookie_jar:
                    if cookie.key == 'sessionid':
                        session_id_value = cookie.value
                        break
                if isvalid and session_id_value:
                    ecode = 200
                    headers['Cookie']=f"csrftoken={csrf_token}; sessionid={session_id_value}"
            self.headers = headers
        if self._client.debug == 1:    
            if ecode == 200: print("[info] [ws] Login success...")
            if ecode == 201: print("[info] [ws] Login as anon success...")
            elif ecode == 202: print("[info] [ws] Incorrect Password...")
        if not isvalid:
            print(f"[info] [ws: {valid_room.status}] The room='{self.name}' doesn't exist")
            return
        Tasks = [asyncio.create_task(self.listen_websocket())]
        asyncio.gather(*Tasks)
    
    async def _send_command(self, command):
        if self._ws and not self._ws.closed:
            await self._ws.send_json(command)

    async def close_session(self):
        if self._session:
            await self._session.close()
