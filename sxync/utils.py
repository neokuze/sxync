import random
import string
import base64
import aiohttp
import asyncio
import re
import socket

from . import constants
from aiohttp.base_protocol import BaseProtocol
from asyncio import streams, transports, get_event_loop

_aiohttp_session = None
cookie_jar = aiohttp.CookieJar(unsafe=False)


def cleanText(text):
    """Regresa texto en minúsculas y sin acentos :> thx linkkg"""
    text = text.lower().strip()
    clean = {
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u"
    }
    for y in clean:
        if y in text:
            text = text.replace(y, clean[y])
    return text


def public_attributes(obj):
    return [
        x for x in set(list(obj.__dict__.keys()) + list(dir(type(obj)))) if x[0] != "_"
    ]


def generate_header():
    key = ''.join(random.choice(string.ascii_letters + string.digits)
                  for _ in range(16)).encode('utf-8')
    headers = {
        'Connection': 'keep-alive, Upgrade',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Host': constants.url,
        'Origin': f'https://{constants.url}',
        'Sec-WebSocket-Version': '13',
        'Sec-WebSocket-Extensions': 'permessage-deflate',
        'Sec-WebSocket-Key': base64.b64encode(key).decode('utf-8'),
        'Upgrade': 'websocket'}
    return headers


async def is_room_valid(name):
    """
    an ugly way to check is exist.
    """
    url = constants.room_url+f"{name}/"
    headers = {'referer': constants.login_url}
    response = await _fetch_html(url, headers={})
    if response['status_code'] == 302:
        return False
    return True


def get_aiohttp_session():
    global _aiohttp_session
    if _aiohttp_session is None:
        conn = aiohttp.TCPConnector(
            limit=200,  # limit conn per host
            limit_per_host=20,  # max limit per route
            keepalive_timeout=30)
        _aiohttp_session = aiohttp.ClientSession(
            connector=conn, cookie_jar=cookie_jar,
            headers={'referer': constants.login_url})
    return _aiohttp_session


def _is_cookie_valid(cj):
    for cookie in cj:
        if cookie.key == 'sessionid':
            return True
    return False


async def _fetch_html(url, headers=None):
    async with get_aiohttp_session().get(url, headers=headers, allow_redirects=False) as response:
        response_headers = response.headers
        redirected_url = response_headers.get('Location')
        status_code = response.status
        html = await response.text()
        return {
            'status_code': status_code,
            'headers': response_headers,
            'redirected_url': redirected_url,
            'html': html
        }


class Jar:
    def __init__(self, username, password):
        self.aiohttp_session = get_aiohttp_session()
        self.html = None
        self.html_post = str()
        self.csrftoken = str()
        self.session_id_value = str()
        self._default_user_name = username
        self._default_password = password
        self._success = None
        self._limit = 70
        self._counter = 0

    def __repr__(self):
        return "[Jar]"

    def __dir__(self):
        return public_attributes(self)

    @property
    def success(self):
        return self._success

    def get(self, html):
        self.html = html
        self.csrftoken = self.extract_csrf_token()

    def extract_csrf_token(self):
        response = self.html['html']
        pattern = r'<input\s+type="hidden"\s+name="csrfmiddlewaretoken"\s+value="([^"]+)"\s*/?>'
        match = re.search(pattern, response)
        if match:
            return match.group(1)
        return None

    def get_session_id(self):
        self.session_id_value = None
        self._success = False
        for cookie in self.aiohttp_session.cookie_jar:
            if cookie.key == 'sessionid':
                self.session_id_value = cookie.value
                self._success = True
                break

    async def login_post(self):
        login_data = {
            'csrfmiddlewaretoken': self.csrftoken,
            'username': self._default_user_name,
            'password': self._default_password}
        while True:
            try:
                self.html_post = await self.aiohttp_session.post(constants.login_url, data=login_data, headers={'referer': constants.login_url})
                home = await self.html_post.text()
                pattern = r'<div\s+class="alert alert-danger error">(.*?)</div>'
                match = re.search(pattern, home, re.DOTALL)
                if match:
                    warn = match.group(1).strip()
                    logging.warning(f"[Warn] {warn}: {self._default_user_name}")
                else:  # /login success
                    self.get_session_id()
                break
            except (aiohttp.client_exceptions.ServerDisconnectedError) as e:
                await asyncio.sleep(5)

    async def get_new_session(self):
        try:
            login = await _fetch_html(constants.login_url, headers={'referer': constants.login_url})
            self.get(login)
            return True
        except aiohttp.client_exceptions.ClientConnectorError:
            await asyncio.sleep(5)  # /try again
            return False


class Struct:
    def __init__(self, struct_name, **entries):
        self._name = struct_name or self.__class__.__name__
        self.__dict__.update(entries)

    def __dir__(self):
        return public_attributes(self)

    def __repr__(self):
        return f"<{self._name}>"
