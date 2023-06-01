import logging

from sqlalchemy.exc import OperationalError

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
        return ActDetail.query.filter(ActDetail.status == 1)
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


def convert_orders_act_join_res(orders_act_join_res):
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
        
        res.append(res_item)
    return res


def query_orders_by_user_id(user_id):
    try:
        orders_act_join_res = ActOrders.query.filter(ActOrders.user_id == user_id).join(UserDetail, ActOrders.user_id == UserDetail.id).order_by(ActOrders.created_at.desc()).limit(10).all()
        return list(ordersList)
    except Exception as e:
        logger.info("query_user_by_id errorMsg= {} ".format(e))
    return []
    