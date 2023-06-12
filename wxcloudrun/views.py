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
from wxcloudrun.dao import get_act_detail_by_id, query_order_by_order_id, query_group_purchase_info_by_id
from wxcloudrun.dao import query_group_purchase_info_by_user_act_id
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

DEFAULT_NICKNAME = '微信用户'
DEFAULT_AVATAR_URL = 'https://thirdwx.qlogo.cn/mmopen/vi_32/POgEwh4mIHO4nibH0KlMECNjjGxQUq24ZEaGT4poC6icRiccVGKSyXwibcPq4BWmiaIGuG1icwxaQX6grC9VemZoJ8rg/132'


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
    if user_info.user_role is not None:
        res['user_role'] = user_info.user_role
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
            "register_from_id": utils.dict_get_default(params, "register_from_id", 0),
            "register_from_chn": utils.dict_get_default(params, "register_from_chn", "")
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
        "isValidPhoneNumber": utils.dict_get_default(session_info_dict, "is_valid_phone_number", False),
        "userRole": utils.dict_get_default(session_info_dict, "user_role", "")
    }
    if utils.is_debug(params):
        res_data['openid'] = open_id
        res_data['sessionKey'] = session_key
    return make_succ_response(res_data)


def convert_act_detail_info(item):
    res = {}
    if item.id is not None:
        res['id'] = item.id
    if item.host_id is not None:
        res['hostID'] = item.host_id
    if item.loc is not None:
        res['loc'] = item.loc
    if item.name is not None:
        res['name'] = item.name
    if item.price is not None:
        res['price'] = float(item.price)
    if item.total_num is not None:
        res['totalNum'] = item.total_num
    if item.cur_num is not None:
        res['curNum'] = item.cur_num
    if item.start_at is not None:
        res['startAt'] = item.start_at.strftime("%Y%m%d %H:%M:%S")
    if item.end_at is not None:
        res['endAt'] = item.end_at.strftime("%Y%m%d %H:%M:%S")
    if item.post_url is not None:
        res['postUrl'] = item.post_url
    if item.short_cut_url is not None:
        res['shortCutUrl'] = item.short_cut_url
    if item.status is not None:
        res['status'] = item.status
    if item.need_group_purchase is not None:
        res['needGroupPurchase'] = item.need_group_purchase
    return res


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


def make_act_details(act_details):
    res_item = {}
    for act, user, order in act_details:
        if user is None:
            continue
        res_item = convert_act_detail_info(act)
        res_item["hostAvatarUrl"] = user.avatar_url
        res_item["hostName"] = user.nickname
        res_item["isBuy"] = 0
        if order is not None and order.status == 0:
            res_item["isBuy"] = 1
            break
    return res_item


def make_group_purchase_info(group_purchase_info):
    res = []
    for order, user in group_purchase_info:
        if user is None:
            continue
        res_item = {
            'groupUserName': user.nickname,
            'groupUserAvatarUrl': user.avatar_url
        }
        res.append(res_item)
    return res


def get_group_purchase_id(info):
    for order, user in info:
        if order is None:
            continue
        return order.group_purchase_id
    return 0


@app.route('/get_act_detail', methods=['POST'])
def get_act_detail():
    params = request.get_json()
    if 'act_id' not in params:
        return make_err_response("missing act_id field")
    if 'user_id' not in params:
        return make_err_response("missing user_id field")
    group_purchase_id = utils.dict_get_default(params, 'group_purchase_id', 0)
    act_id = params['act_id']
    user_id = params['user_id']
    act_details = get_act_detail_by_id(int(act_id))
    if len(act_details) <= 0:
        return make_err_response("act detail missing")
    group_purchase_info = query_group_purchase_info_by_user_act_id(user_id, act_id)
    print("group_purchase_id1: ", group_purchase_id, len(group_purchase_info), sep=" ")
    if len(group_purchase_info) == 0 and group_purchase_id != 0:
        group_purchase_info = query_group_purchase_info_by_id(group_purchase_id)
    print("group_purchase_id2: ", group_purchase_id, len(group_purchase_info), sep=" ")
    group_purchase_id = get_group_purchase_id(group_purchase_info)
    return make_succ_response({
        "actInfo": make_act_details(act_details),
        "groupPurchaseInfo": make_group_purchase_info(group_purchase_info),
        "groupPurchaseID": group_purchase_id
    })


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


@app.route('/check_user_info', methods=['POST'])
def check_user_info():
    params = request.get_json()
    if 'session_id' not in params:
        return make_err_response("missing session_id field")
    if 'user_id' not in params:
        return make_err_response("missing session_id field")
    user_id = params['user_id']
    user_info = query_user_by_id(user_id)
    if user_info is None:
        return make_err_response("user does not exists")
    avatar_url = user_info.avatar_url
    nickname = user_info.nickname
    res = {
        'isSetUserName': 1,
        'isSetAvatarUrl': 1
    }
    if nickname is None or nickname == DEFAULT_NICKNAME or len(nickname) == 0:
        res['isSetUserName'] = 0
    if avatar_url is None or avatar_url == DEFAULT_AVATAR_URL or len(avatar_url.strip()) == 0:
        res['isSetAvatarUrl'] = 0
    res['userName'] = user_info.nickname
    res['userAvatarUrl'] = user_info.avatar_url
    return make_succ_response(res)


def make_orders_act_join_res_dict(orders_act_join_res):
    res = []
    for order, act_detail, user_detail in orders_act_join_res:
        if user_detail is None:
            continue
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
        if user_detail.nickname is not None:
            res_item['hostName'] = user_detail.nickname
        
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
    act.cur_num += 1
    if act.cur_num > act.total_num:
        return make_succ_response(0)
    if not update_database():
        return make_err_response("update act failed")
    if act is None:
        return make_err_response("invalid act")
    new_order = insert_new_order(params, act)
    if new_order is None:
        return make_err_response("insert_new_order failed")
    res = {
        'code': 1,
        'groupPurchaseID': new_order.group_purchase_id
    }
    return make_succ_response(res)


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


@app.route('/cancel_order', methods=['POST'])
def cancel_order():
    params = request.get_json()
    if 'order_id' not in params:
        return make_err_response("missing order_id field")
    if 'user_id' not in params:
        return make_err_response("missing user_id field")
    user_id = params['user_id']
    order_id = params['order_id']
    order = query_order_by_order_id(order_id)
    if order is None:
        return make_err_response("order not exists")
    act_id = order.act_id
    act = query_act_by_id(act_id)
    if act is None:
        return make_err_response("act not exists")
    if order.user_id != user_id:
        return make_err_response("order not match user")
    if act.cur_num > 0:
        act.cur_num -= 1
    order.status = 1
    if update_database():
        return make_succ_response(1)
    return make_succ_response(0)

