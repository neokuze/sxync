import random
import string
import base64

from . import constants
from bs4 import BeautifulSoup

def cleanText(text):
    """Regresa texto en minúsculas y sin acentos :> thx linkkg"""
    text = text.lower().strip()
    clean = {
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
        "@": "", "?": "", "!": "!", ",": "", ".": "", "¿": ""
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
    key = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(16)).encode('utf-8')
    headers = {
        'Connection': 'keep-alive, Upgrade',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'en-US,en;q=0.5',
        'Origin': f'https://{constants.url}',
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
    
async def is_room_valid(session, name):
    """
    an ugly way to check is exist.
    """
    room_valid = await session.get(constants.room_url+f"{name}/", headers={'referer': constants.login_url})
    soup = BeautifulSoup(await room_valid.text(), 'html.parser')
    isval = soup.find('button', {'class': 'btn btn-primary'})
    if isval == None:
        return True
    return False
    