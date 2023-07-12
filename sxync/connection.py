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
logging.basicConfig(level=logging.DEBUG)

def trace_request_ctx(session, context, params):
    pass

def trace_request_headers(session, context, params):
    pass

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
        try:
            self._ws = await self._session.ws_connect(self._ws_url, headers=self.headers)
            if int(self.client.debug) <= 2:
                logging.info("Conexión exitosa al websocket: %s", self._ws_url)
        except Exception as e:
            if int(self.client.debug) <= 2:
                logging.error("Error al conectar al websocket: %s", str(e))
        while True:
            try:
                if self._ws.closed:
                    break
                logging.debug(f"[ws: {self.name}] Esperando mensaje del websocket...")
                msg = await self._ws.receive()
                if self._first_time:
                    await self.on_connect()
                    self._first_time = False
                try:
                    assert msg.type is aiohttp.WSMsgType.TEXT
                    logging.debug("Mensaje recibido del websocket: %s", msg)
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
                            if int(self.client.debug) <= 1:
                                logging.error("Error al ejecutar comando: %s", cmd, exc_info=True)
                                traceback.print_exc(file=sys.stderr)
                    elif int(self.client.debug) <= 2:
                        logging.error("Error de comando no manejado: %s | {}".format(kwargs),cmd, exc_info=True)
                except AssertionError: pass
            except ConnectionResetError:
                if int(self.client.debug) <= 1:
                    logging.warning("Conexión websocket restablecida.")
                break
        Tasks = [asyncio.create_task(self.listen_websocket())]
        asyncio.gather(*Tasks)
        
                    

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
        logger = logging.getLogger('aiohttp.client')
        logger.setLevel(logging.DEBUG)
        
        cookie_jar=aiohttp.CookieJar(unsafe=False)
        self._session =  aiohttp.ClientSession(cookie_jar=cookie_jar, headers={'referer': self._login_url})
        connector = aiohttp.TCPConnector(ssl=False)
        connector._trace_config = aiohttp.TraceConfig()
        connector._trace_config.on_request_start.append(trace_request_ctx)
        connector._trace_config.on_request_end.append(trace_request_headers)

        self._session._connector = connector
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
                    headers['Cookie']=f"csrftoken={csrf_token}; sessionid={session_id_value}"
            if self._client.debug <= 1:    
                if ecode == 200: logging.info("[info] [ws] Login success...")
                if ecode == 201: logging.info("[info] [ws] Login as anon success...")
                if ecode == 202: logging.info("[info] [ws] Incorrect Password...")
            self.headers = headers
            if isvalid == None:
                Tasks = [asyncio.create_task(self.listen_websocket())]
                asyncio.gather(*Tasks)
            else:
                await self._client.leave_room(self.name)
                raise InvalidRoom("The room doesn't exist.")
    
    async def _send_command(self, command):
        if self._ws and not self._ws.closed:
            await self._ws.send_json(command)

    async def close_session(self):
        if self._session:
            await self._session.close()
