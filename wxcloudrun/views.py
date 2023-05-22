import json
import redis
import requests

import wxcloudrun.utils as utils

from datetime import datetime
from flask import render_template, request
from run import app
from wxcloudrun.dao import delete_counterbyid, query_counterbyid, insert_counter, update_counterbyid
from wxcloudrun.model import Counters
from wxcloudrun.response import make_succ_empty_response, make_succ_response, make_err_response


APPID = 'wx751ba538e01e40f6'
SECRET = 'ee7eb9b1076e81941817e84d2f95a8db'
REDIS_HOST = 'r-8vb77upzev9wod2p2dpd.redis.zhangbei.rds.aliyuncs.com'
REDIS_PORT = 6379
REDIS_PWD = 'CAMPparty123456'
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PWD)
SESSION_EXPIRE_TS = 24*3600
SESSION_ID_PREFIX = 'session_id_'


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
    try:
        session_info_obj = json.loads(rsp.text)
    except:
        return make_err_response("session info loads failed")
    if 'session_key' not in session_info_obj or 'openid' not in session_info_obj:
        return make_err_response("session info missing field")
    openid = session_info_obj['openid']
    session_key = session_info_obj['session_key']
    session_id = SESSION_ID_PREFIX + str(abs(hash(session_key + openid)))
    redis_client.hset(session_id, mapping={"session_key": session_key, "openid": openid})
    redis_client.expire(session_id, SESSION_EXPIRE_TS)

    res_data = {"sessionID": session_id}
    if utils.is_debug(params):
        res_data['openid'] = openid
        res_data['sessionKey'] = session_key
    return make_succ_response(res_data)


@app.route('/list_all_rec_acts', methods=['POST'])
def get_session_info():
    pass
