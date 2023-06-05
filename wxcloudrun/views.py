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
from wxcloudrun.dao import query_user_by_id, query_orders_by_user_id, update_database, insert_new_order
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
            counter.created_at = utils.get_shanghai_now()
            counter.updated_at = utils.get_shanghai_now()
            insert_counter(counter)
        else:
            counter.id = 1
            counter.count += 1
            counter.updated_at = utils.get_shanghai_now()
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


def make_user_info_dict(user_info):
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
        is_valid_phone_number = 0
        if check_valid_phone_number(user_info.phone_number):
            is_valid_phone_number = 1
        res['is_valid_phone_number'] = is_valid_phone_number
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
            "open_id": open_id,
            "register_from_id": utils.dict_get_default(params, 0),
            "register_from_chn": utils.dict_get_default(params, "")
        }
        if insert_user_detail(session_info_dict) == False:
            return make_err_response("insert user detail faild")
        user_info = query_user_by_open_id(open_id)
    else:
        session_info_dict = make_user_info_dict(user_info)
    session_info_dict['session_key'] = session_key
    session_info_dict['open_id'] = open_id

    redis_client.hset(session_id, mapping=session_info_dict)
    redis_client.expire(session_id, SESSION_EXPIRE_TS)

    res_data = {
        "sessionID": session_id,
        "userID": user_info.id,
        "isValidPhoneNumber": utils.dict_get_default(session_info_dict, "is_valid_phone_number", False)
    }
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
        for act, user in _input:
            res_item = convert_act_detail_info(act)
            res_item["hostAvatarUrl"] = user.avatar_url
            res_item["hostNickname"] = user.nickname
            res.append(res_item)
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
    if 'user_id' not in params:
        return make_err_response("missing session_id field")
    user_id = params['user_id']
    user_info = query_user_by_id(user_id)
    if user_info is None:
        return make_err_response("user does not exists")
    phone = user_info.phone_number
    if phone is None:
        make_succ_response(0)
    if check_valid_phone_number(str(phone)):
        return make_succ_response(1)
    return make_succ_response(0)


def make_orders_act_join_res_dict(orders_act_join_res):
    res = []
    for order, act_detail in orders_act_join_res:
        res_item = {}
        if order.id is not None:
            res_item['id'] = order.id
        if order.user_id is not None:
            res_item['userID'] = order.user_id
        if order.act_id is not None:
            res_item['actID'] = order.act_id
        if order.created_at is not None:
            res_item['createdAt'] = order.created_at.strftime("%Y%m%d %H:%M:%S")
        if order.status is not None:
            res_item['status'] = order.status
        if order.amount is not None:
            res_item['amount'] = float(order.amount)
        if order.count is not None:
            res_item['count'] = order.count
        if act_detail.start_at is not None:
            res_item['actStartAt'] = act_detail.start_at.strftime("%Y%m%d %H:%M:%S")
        if act_detail.status is not None:
            res_item['actStatus'] = act_detail.status
        if act_detail.short_cut_url is not None:
            res_item['actShortCutUrl'] = act_detail.short_cut_url
        if act_detail.name is not None:
            res_item['actName'] = act_detail.name
        if act_detail.loc is not None:
            res_item['actLoc'] = act_detail.loc
        
        res.append(res_item)
    return res


@app.route('/get_user_profile', methods=['POST'])
def get_user_profile():
    params = request.get_json()
    if 'user_id' not in params:
        return make_err_response("missing user_id field")
    user_id = params['user_id']
    user_info = query_user_by_id(user_id)
    if user_info is None:
        return make_err_response("user is not valid")
    orders_list = query_orders_by_user_id(user_id)

    res = {
        "userInfo": make_user_info_dict(user_info),
        "ordersList": make_orders_act_join_res_dict(orders_list)
    }

    return make_succ_response(res)


@app.route('/update_user_avatar', methods=['POST'])
def update_user_avatar():
    params = request.get_json()
    if 'user_id' not in params:
        return make_err_response("missing user_id field")
    if 'avatar_url' not in params:
        return make_err_response("missing avatar_url field")
    if 'session_id' not in params:
        return make_err_response("missing session_id field")
    user_id = params['user_id']
    session_id = params['session_id']
    avatar_url = params['avatar_url']
    user_info = query_user_by_id(user_id)
    if user_info is None:
        return make_err_response("user is not valid")
    user_info.avatar_url = avatar_url
    if not update_database():
        return make_err_response("update database failed")
    redis_client.hset(session_id, "avatar_url", avatar_url)
    return make_succ_response(1)


@app.route('/update_user_name', methods=['POST'])
def update_user_name():
    params = request.get_json()
    if 'user_id' not in params:
        return make_err_response("missing user_id field")
    if 'new_name' not in params:
        return make_err_response("missing new_name field")
    if 'session_id' not in params:
        return make_err_response("missing session_id field")
    user_id = params['user_id']
    session_id = params['session_id']
    new_name = params['new_name']
    user_info = query_user_by_id(user_id)
    if user_info is None:
        return make_err_response("user is not valid")
    user_info.nickname = new_name
    if not update_database():
        return make_err_response("update database failed")
    redis_client.hset(session_id, "nickname", new_name)
    return make_succ_response(1)


@app.route('/buy_ticket', methods=['POST'])
def buy_ticket():
    params = request.get_json()
    if 'user_id' not in params:
        return make_err_response("missing user_id field")
    if 'session_id' not in params:
        return make_err_response("missing session_id field")
    if 'act_id' not in params:
        return make_err_response("missing act_id field")
    params['count'] = 1
    act = query_act_by_id(params["act_id"])
    if act is None:
        return make_err_response("invalid act")
    if not insert_new_order(params, act):
        return make_err_response("insert_new_order failed")
    return make_succ_response(1)


@app.route('/decrypt_user_phone', methods=['POST'])
def decrypt_user_phone():
    params = request.get_json()
    if 'user_id' not in params:
        return make_err_response("missing user_id field")
    if 'session_id' not in params:
        return make_err_response("missing session_id field")
    if 'encrypted_data' not in params:
        return make_err_response("missing encrypted_data field")
    if 'iv' not in params:
        return make_err_response("missing iv field")
    user_id = params['user_id']
    session_id = params['session_id']
    encrypted_data = params['encrypted_data']
    iv = params['iv']
    session_key = redis_client.hget(session_id, "session_key")
    if session_key is None or session_key == "" or len(session_key) == 0:
        return make_err_response("invalid session_key")
    try:
        phone_data = utils.decrypt_data(encrypted_data, session_key, iv)
        phone_data = json.loads(phone_data)
        phone_number = phone_data['purePhoneNumber']
        user = query_user_by_id(user_id)
        if user is None:
            return make_err_response("invalid user")
        user.phone_number = phone_number
        if not update_database():
            return make_err_response("update_database failed")
        redis_client.hset(session_id, "phone_number", phone_number)
    except Exception as e:
        return make_err_response("decrypt data error")
    return make_succ_response({"res": 1, "phone": phone_number})

