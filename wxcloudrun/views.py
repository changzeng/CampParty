import re
import json
import redis
import requests

import wxcloudrun.utils as utils

from datetime import datetime
from flask import render_template, request
from flask import jsonify
from run import app
from wxcloudrun.dao import delete_counterbyid, query_counterbyid, insert_counter, update_counterbyid
from wxcloudrun.dao import query_all_valid_act, query_act_by_id, query_user_by_open_id, insert_user_detail
from wxcloudrun.model import Counters
from wxcloudrun.response import make_succ_empty_response, make_succ_response, make_err_response


APPID = 'wx751ba538e01e40f6'
SECRET = 'ee7eb9b1076e81941817e84d2f95a8db'
REDIS_HOST = 'r-8vb77upzev9wod2p2dpd.redis.zhangbei.rds.aliyuncs.com'
REDIS_PORT = 6379
REDIS_PWD = 'CAMPparty123456'
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PWD)
SESSION_EXPIRE_TS = 2*7*24*3600
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


def make_session_info_dict(user_info):
    res = {}
    if user_info.open_id is not None:
        res['open_id'] = user_info.open_id
    if user_info.avatar_url is not None:
        res['avatar_url'] = user_info.avatar_url
    if user_info.city is not None:
        res['city'] = user_info.city
    if user_info.country is not None:
        res['country'] = user_info.country
    if user_info.gender is not None:
        res['gender'] = user_info.gender
    if user_info.language is not None:
        res['language'] = user_info.language
    if user_info.nickname is not None:
        res['nickname'] = user_info.nickname
    if user_info.phone_number is not None:
        res['phone_number'] = user_info.phone_number
    return res


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
    open_id = session_info_obj['openid']
    session_key = session_info_obj['session_key']
    session_id = SESSION_ID_PREFIX + str(abs(hash(session_key + open_id)))

    user_info = query_user_by_open_id(open_id)
    session_info_dict = {}
    if user_info is None:
        session_info_dict = {
            "open_id": open_id
        }
        if insert_user_detail(session_info_dict) == False:
            return make_err_response("insert user detail faild")
        user_info = query_user_by_open_id(open_id)
    else:
        session_info_dict = make_session_info_dict(user_info)
    session_info_dict['session_key'] = session_key
    session_info_dict['open_id'] = open_id

    redis_client.hset(session_id, mapping=session_info_dict)
    redis_client.expire(session_id, SESSION_EXPIRE_TS)

    res_data = {"sessionID": session_id, "userID": user_info.id}
    if utils.is_debug(params):
        res_data['openid'] = open_id
        res_data['sessionKey'] = session_key
    return make_succ_response(res_data)


def convert_act_detail_info(item):
    return {
        "id": item.id,
        "hostID": item.host_id,
        "loc": item.loc,
        "name": item.name,
        "price": float(item.price),
        "totalNum": item.total_num,
        "curNum": item.cur_num,
        "startAt": item.start_at.strftime("%Y%m%d %H:%M:%S"),
        "endAt": item.end_at.strftime("%Y%m%d %H:%M:%S"),
        "postUrl": item.post_url,
        "shortCutUrl": item.short_cut_url,
        "status": item.status
    }


@app.route('/list_all_rec_acts', methods=['POST'])
def list_all_rec_acts():
    all_valid_acts = query_all_valid_act()
    def make_resp(_input):
        res = []
        for item in _input:
            res.append(convert_act_detail_info(item))
        return res
    return make_succ_response(make_resp(all_valid_acts))


@app.route('/get_act_detail', methods=['POST'])
def get_act_detail():
    params = request.get_json()
    if 'id' not in params:
        return make_err_response("missing id field")
    act_detail = query_act_by_id(int(params['id']))
    if act_detail is None:
        return make_err_response("act detail missing")
    return make_succ_response(convert_act_detail_info(act_detail))


def check_valid_phone_number(phone):
    pattern = re.compile(r'^1[3-9]\d{9}$')
    match = pattern.match(phone)
    return match is not None


@app.route('/send_phone_code', methods=['POST'])
def send_phone_code():
    params = request.get_json()
    if 'phone' not in params:
        return make_err_response("missing phone field")
    if 'session_id' not in params:
        return make_err_response("missing session_id field")
    session_id = params['session_id']
    phone = params['phone']
    if not check_valid_phone_number(phone):
        return make_err_response("invalid phone number")
    phone_validation_code = "123"
    redis_client.hset(session_id, mapping={'phone': phone, 'phone_validation_code': phone_validation_code})
    redis_client.expire(session_id, SESSION_EXPIRE_TS)


@app.route('/put_user_phone', methods=['POST'])
def put_user_phone():
    params = request.get_json()
    if 'phone_validation_code' not in params:
        return make_err_response("missing phone_validation_code field")
    if 'session_id' not in params:
        return make_err_response("missing session_id field")
    
    session_id = params['session_id']
    phone_validation_code = params['phone_validation_code']

    session_data = redis_client.hgetall(session_id)
    if 'phone' not in session_data:
        return make_err_response("session data missing phone field")
    if 'phone_validation_code' not in session_data:
        return make_err_response("session data missing phone_validation_code field")
    server_phone_validation_code = session_data['phone_validation_code']

    if str(server_phone_validation_code) == str(phone_validation_code):
        return make_succ_response(1)
    return make_succ_response(0)


@app.route('/check_user_phone', methods=['POST'])
def check_user_phone():
    params = request.get_json()
    if 'session_id' not in params:
        return make_err_response("missing session_id field")
    session_id = params['params']
    session_data = redis_client.hgetall(session_id)
    if 'open_id' not in session_data:
        return make_err_response("session data missing open_id field")
    open_id = session_data['open_id']
    user_info = query_user_by_open_id(open_id)
    if user_info is None:
        return make_err_response("user does not exists")
    phone = user_info.phone_number
    if check_valid_phone_number(phone):
        return make_succ_response(1)
    return make_succ_response(0)
    
