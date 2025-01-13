import random
import string
import base64
import aiohttp
import asyncio
import re
import logging
import json
from . import constants


class pattern:
    csrf_token = r'<input\s+type="hidden"\s+name="csrfmiddlewaretoken"\s+value="([^"]+)"\s*/?>'
    login_success = r'<div\s+class="alert alert-danger error">(.*?)</div>'

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
    response = await _fetch_html(url, headers={}, allow_redirects=False)
    if response['status_code'] == 302:
        return False
    return True


def _is_cookie_valid(cj):
    for cookie in cj:
        if cookie.key == 'sessionid':
            return True
    return False


async def _fetch_html(url, headers={}, cookie_jar=None, allow_redirects=True, data=None, action='get'):
    headers.update({'referer': constants.login_url})
    conn = aiohttp.TCPConnector(
        limit=100,  # limit conn per host
        limit_per_host=10,  # max limit per route
        keepalive_timeout=30)
    status_code, response_headers, redirected_url, html = None, None, None, None
    session = aiohttp.ClientSession(connector=conn, cookie_jar=cookie_jar,
            headers=headers)
    if action == "get":
        response = await session.get(url, headers=headers, allow_redirects=allow_redirects, data=data)
    elif action == "post":
        response = await session.post(url, headers=headers, allow_redirects=allow_redirects, data=data)
    response_headers = response.headers
    redirected_url = response_headers.get('Location')
    status_code = response.status
    html = await response.text()
    await session.close()
    return {
            'status_code': status_code,
            'headers': response_headers,
            'redirected_url': redirected_url,
            'html': html
        }


class Jar:
    def __init__(self, username, password, loop):
        self.loop = loop
        self._default_user_name = username
        self._default_password = password
        self._limit = 70 # do not modify this
        self._counter = 0
        self._reset()

    def _reset(self):
        self.html = None
        self.html_post = str()
        self.csrftoken = str()
        self.session_id_value = str()
        self._success = None
        self._profile = str()
        self.cookie_jar = aiohttp.CookieJar(unsafe=False, loop=self.loop)

    def __repr__(self):
        return "[Jar]"

    def __dir__(self):
        return public_attributes(self)

    @property
    def success(self):
        return self._success

    def extract_csrf_token(self, html=None):
        response = self.html['html'] if None else html
        match = re.search(pattern.csrf_token, response)
        if match:
            return match.group(1)
        return None

    def get_session_id(self):
        self.session_id_value = None
        self._success = False
        for cookie in self.cookie_jar:
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
                received_data = await _fetch_html(constants.login_url, cookie_jar=self.cookie_jar, data=login_data, action='post')
                match = re.search(pattern.login_success, received_data['html'], re.DOTALL)
                if not match:
                    self.get_session_id() #Login success 
                else:
                    warn = match.group(1).strip()
                    logging.warning(f"[Warn] {warn}: {self._default_user_name}")
                break
            except (aiohttp.client_exceptions.ServerDisconnectedError) as e:
                await asyncio.sleep(5)

    async def get_new_session(self):
        try:
            data = await _fetch_html(constants.login_url, cookie_jar=self.cookie_jar)
            self.csrftoken = self.extract_csrf_token(data['html']) #need this when is reconnected
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

def cleanText(text):
    text = text.lower().strip()
    clean = {
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u"
    }
    for y in clean:
        if y in text:
            text = text.replace(y, clean[y])
    return text

def remove_html_tags(text):
    text = " {} ".format(text)
    clean_text = re.sub(r'<[^>]+>', '', text)
    return clean_text

async def get_profile():
    fetch_data = await _fetch_html(constants.login_url, headers={'Accept':'application/json'})
    _json = fetch_data['html'].split("<script id=\"user_json\" type=\"application/json\">")[1].split("</script>")[0]
    data = json.loads(_json)
    return data