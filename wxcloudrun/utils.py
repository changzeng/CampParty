import json
import base64
import pytz
import logging
import os

from Crypto.Cipher import AES
from datetime import datetime


file_path = os.path.abspath(os.path.dirname(__file__)) + '/app.log'
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler = logging.FileHandler(file_path)
handler.setLevel(logging.INFO)
handler.setFormatter(formatter)
logger.addHandler(handler)


def decrypt_data(encrypted_data, session_key, iv):
    encrypted_data = base64.b64decode(encrypted_data)
    iv = base64.b64decode(iv)
    session_key = base64.b64decode(session_key)
    cipher = AES.new(session_key, AES.MODE_CBC, iv)
    decrypted = cipher.decrypt(encrypted_data)
    result = decrypted[:-ord(decrypted[len(decrypted) - 1:])]
    result = result.decode('utf8')
    return result


def get_session_data(redis_client, uuid):
    return json.loads(redis_client.hgetall(uuid))


def is_debug(params):
    if 'debug' not in params:
        return False
    if params['debug'] == 1:
        return True
    if params['debug'] == '1':
        return True
    return False


def dict_get_default(_dict, _key, _default_val):
    if _key not in _dict:
        return _default_val
    return _dict[_key]


def get_shanghai_now():
    tz = pytz.timezone('Asia/Shanghai')
    return datetime.now(tz=tz)