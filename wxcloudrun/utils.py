import json
import base64

from Crypto.Cipher import AES


def decrypt_data(encrypted_data, session_key, iv):
    encrypted_data = base64.b64decode(encrypted_data)
    iv = base64.b64decode(iv)
    session_key = base64.b64decode(session_key)
    cipher = AES.new(session_key, AES.MODE_CBC, iv)
    decrypted = cipher.decrypt(encrypted_data)
    result = decrypted[:-ord(decrypted[len(decrypted) - 1:])]
    result = result.decode('utf8')
    return result


def get_session_info(redis_client, uuid):
    return json.loads(redis_client.hgetall(uuid))
