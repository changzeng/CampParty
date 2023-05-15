import redis
import requests
import base64

from Crypto.Cipher import AES
from datetime import datetime
from flask import render_template, request
from run import app
from wxcloudrun.dao import delete_counterbyid, query_counterbyid, insert_counter, update_counterbyid
from wxcloudrun.model import Counters
from wxcloudrun.response import make_succ_empty_response, make_succ_response, make_err_response


APPID = 'wx751ba538e01e40f6'
SECRET = 'ee7eb9b1076e81941817e84d2f95a8db'

# redis_client = redis.Redis(host='0.0.0.0', port=6379)


@app.route('/')
def index():
    """
    :return: 返回index页面
    """
    return render_template('index.html')


@app.route('/api/count', methods=['POST'])
def count():
    """
    :return:计数结果/清除结果
    """

    # 获取请求体参数
    params = request.get_json()

    # 检查action参数
    if 'action' not in params:
        return make_err_response('缺少action参数')

    # 按照不同的action的值，进行不同的操作
    action = params['action']

    # 执行自增操作
    if action == 'inc':
        counter = query_counterbyid(1)
        if counter is None:
            counter = Counters()
            counter.id = 1
            counter.count = 1
            counter.created_at = datetime.now()
            counter.updated_at = datetime.now()
            insert_counter(counter)
        else:
            counter.id = 1
            counter.count += 1
            counter.updated_at = datetime.now()
            update_counterbyid(counter)
        return make_succ_response(counter.count)

    # 执行清0操作
    elif action == 'clear':
        delete_counterbyid(1)
        return make_succ_empty_response()

    # action参数错误
    else:
        return make_err_response('action参数错误')


@app.route('/api/count', methods=['GET'])
def get_count():
    """
    :return: 计数的值
    """
    counter = Counters.query.filter(Counters.id == 1).first()
    return make_succ_response(0) if counter is None else make_succ_response(counter.count)


@app.route('/get_session_info', methods=['POST'])
def get_session_info():
    params = request.get_json()
    if 'code' not in params:
        return make_err_response('缺少code参数')
    code = params['code']
    url = 'https://api.weixin.qq.com/sns/jscode2session?appid={0}&secret={1}&js_code={2}&grant_type=authorization_code'.format(
        APPID, SECRET, code)
    rsp = requests.get(url)
    return make_succ_response(rsp.text)


@app.route('/decrypt_data', methods=['POST'])
def decrypt_data():
    params = request.get_json()
    if 'encryptedData' not in params:
        return make_err_response('缺少encryptedData参数')
    if 'iv' not in params:
        return make_err_response('缺少iv参数')
    if 'sessionKey' not in params:
        return make_err_response('缺少sessionKey参数')
    iv = params['iv']
    session_key = params['sessionKey']
    encrypted_data = params['encryptedData']

    encrypted_data = base64.b64decode(encrypted_data)
    iv = base64.b64decode(iv)
    session_key = base64.b64decode(session_key)
    cipher = AES.new(session_key, AES.MODE_CBC, iv)
    decrypted = cipher.decrypt(encrypted_data)
    result = decrypted[:-ord(decrypted[len(decrypted) - 1:])]
    result = result.decode('utf8')
    return make_succ_response(result)
