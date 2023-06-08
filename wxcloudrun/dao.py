import time
import logging

import wxcloudrun.utils as utils

from sqlalchemy.exc import OperationalError
from datetime import datetime
from wxcloudrun import db
from wxcloudrun.model import Counters
from wxcloudrun.model import ActDetail
from wxcloudrun.model import UserDetail
from wxcloudrun.model import ActOrders

# 初始化日志
logger = logging.getLogger('log')


def query_counterbyid(id):
    """
    根据ID查询Counter实体
    :param id: Counter的ID
    :return: Counter实体
    """
    try:
        return Counters.query.filter(Counters.id == id).first()
    except OperationalError as e:
        logger.info("query_counterbyid errorMsg= {} ".format(e))
        return None


def delete_counterbyid(id):
    """
    根据ID删除Counter实体
    :param id: Counter的ID
    """
    try:
        counter = Counters.query.get(id)
        if counter is None:
            return
        db.session.delete(counter)
        db.session.commit()
    except OperationalError as e:
        logger.info("delete_counterbyid errorMsg= {} ".format(e))


def insert_counter(counter):
    """
    插入一个Counter实体
    :param counter: Counters实体
    """
    try:
        db.session.add(counter)
        db.session.commit()
    except OperationalError as e:
        logger.info("insert_counter errorMsg= {} ".format(e))


def update_counterbyid(counter):
    """
    根据ID更新counter的值
    :param counter实体
    """
    try:
        counter = query_counterbyid(counter.id)
        if counter is None:
            return
        db.session.flush()
        db.session.commit()
    except OperationalError as e:
        logger.info("update_counterbyid errorMsg= {} ".format(e))


def query_all_valid_act():
    try:
        return db.session.query(ActDetail, UserDetail).join(UserDetail, ActDetail.host_id == UserDetail.id).filter(ActDetail.status == 1).all()
    except OperationalError as e:
        logger.info("query_all_valid_act errorMsg= {} ".format(e))
    return []


def query_act_by_id(id):
    try:
        actList = ActDetail.query.filter(ActDetail.id == id)
        actList = list(actList)
        if len(actList) >= 1:
            return actList[0]
        return None
    except Exception as e:
        logger.info("query_act_by_id errorMsg= {} ".format(e))
    return None


def get_act_detail_by_id(id):
    try:
        return db.session.query(ActDetail, UserDetail, ActOrders).filter(ActDetail.id == id).join(UserDetail, ActDetail.host_id == UserDetail.id).outerjoin(ActOrders, UserDetail.id == ActOrders.user_id).all()
    except OperationalError as e:
        logger.info("query_all_valid_act errorMsg= {} ".format(e))
    return []


def query_all_act():
    """
    根据ID查询Counter实体
    :param id: Counter的ID
    :return: Counter实体
    """
    try:
        return ActDetail.query.all()
    except OperationalError as e:
        logger.info("query_counterbyid errorMsg= {} ".format(e))
        return []
    return []
    

def insert_new_item(new_item):
    """
    插入一个实体
    :param counter: 实体
    """
    try:
        db.session.add(new_item)
        db.session.commit()
    except OperationalError as e:
        logger.info("insert new_item errorMsg= {} ".format(e))


def query_user_by_open_id(open_id):
    try:
        actList = UserDetail.query.filter(UserDetail.open_id == open_id)
        actList = list(actList)
        if len(actList) >= 1:
            return actList[0]
        return None
    except Exception as e:
        logger.info("query_user_by_open_id errorMsg= {} ".format(e))
    return None


def insert_user_detail(user_detail_info):
    """
    插入一个新的实体
    """
    # try:
    user_detal = UserDetail()
    if 'open_id' in user_detail_info:
        user_detal.open_id = user_detail_info['open_id']
    if 'avatar_url' in user_detail_info:
        user_detal.avatar_url = user_detail_info['avatar_url']
    else:
        user_detal.avatar_url = 'https://thirdwx.qlogo.cn/mmopen/vi_32/POgEwh4mIHO4nibH0KlMECNjjGxQUq24ZEaGT4poC6icRiccVGKSyXwibcPq4BWmiaIGuG1icwxaQX6grC9VemZoJ8rg/132'
    if 'city' in user_detail_info:
        user_detal.city = user_detail_info['city']
    if 'country' in user_detail_info:
        user_detal.country = user_detail_info['country']
    if 'gender' in user_detail_info:
        user_detal.gender = user_detail_info['gender']
    if 'language' in user_detail_info:
        user_detal.language = user_detail_info['language']
    if 'nickname' in user_detail_info:
        user_detal.nickname = user_detail_info['nickname']
    else:
        user_detal.nickname = '微信用户'
    if 'register_from_id' in user_detail_info:
        user_detal.register_from_id = user_detail_info['register_from_id']
    if 'register_from_chn' in user_detail_info:
        user_detal.register_from_chn = user_detail_info['register_from_chn']
    user_detal.register_at = utils.get_shanghai_now()

    db.session.add(user_detal)
    db.session.commit()
    return True
    # except OperationalError as e:
    #     logger.info("insert_new_entity errorMsg= {} ".format(e))
    # return False


def query_user_by_id(id):
    try:
        actList = UserDetail.query.filter(UserDetail.id == id)
        actList = list(actList)
        if len(actList) >= 1:
            return actList[0]
        return None
    except Exception as e:
        logger.info("query_user_by_id errorMsg= {} ".format(e))
    return None


def query_orders_by_user_id(user_id):
    try:
        orders_act_join_res = db.session.query(ActOrders, ActDetail, UserDetail).filter(ActOrders.user_id == user_id).join(ActDetail, ActOrders.act_id == ActDetail.id).join(UserDetail, ActOrders.user_id == UserDetail.id).order_by(ActOrders.created_at.desc()).limit(4).all()
        return list(orders_act_join_res)
    except Exception as e:
        logger.info("query_orders_by_user_id errorMsg= {} ".format(e))
    return []


def update_database():
    try:
        db.session.flush()
        db.session.commit()
        return True
    except OperationalError as e:
        logger.info("update_database errorMsg= {} ".format(e))
        return False
    except Exception as e:
        logger.info("update_database errorMsg= {} ".format(e))
    return True


def insert_new_order(params, act):
    new_order = ActOrders()
    new_order.user_id = params['user_id']
    new_order.act_id = params['act_id']
    new_order.count = params['count']
    new_order.amount = params['count'] * act.price
    new_order.status = 0
    new_order.created_at = utils.get_shanghai_now()
    new_order.group_purchase_id = hash(str(params['act_id'])+":"+str(params['user_id'])+":"+str(time.time()))

    try:
        db.session.add(new_order)
        db.session.commit()
    except OperationalError as e:
        logger.info("insert_new_order errorMsg= {} ".format(e))
        return None
    return new_order


def query_order_by_order_id(order_id):
    try:
        ordersList = ActOrders.query.filter(ActOrders.id == order_id)
        ordersList = list(ordersList)
        if len(ordersList) >= 1:
            return ordersList[0]
        return None
    except Exception as e:
        logger.info("query_order_by_order_id errorMsg= {} ".format(e))
    return None


def delete_item(item):
    try:
        db.session.delete(item)
        db.session.commit()
        return True
    except OperationalError as e:
        logger.info("delete_item errorMsg= {} ".format(e))
    return False
