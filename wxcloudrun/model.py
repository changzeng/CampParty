from decimal import Decimal
from datetime import datetime

from wxcloudrun import db


# 计数表
class Counters(db.Model):
    # 设置结构体表格名称
    __tablename__ = 'Counters'

    # 设定结构体对应表格的字段
    id = db.Column(db.Integer, primary_key=True)
    count = db.Column(db.Integer, default=1)
    created_at = db.Column('createdAt', db.TIMESTAMP, nullable=False, default=datetime.now())
    updated_at = db.Column('updatedAt', db.TIMESTAMP, nullable=False, default=datetime.now())


class ActDetail(db.Model):
    # 设置结构体表格名称
    __tablename__ = 'act_detail'

    # 设定结构体对应表格的字段
    id = db.Column(db.Integer, primary_key=True)
    host_id = db.Column(db.Integer, nullable=False)
    loc = db.Column(db.String, nullable=False)
    name = db.Column(db.String, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    total_num = db.Column(db.Integer, nullable=False)
    cur_num = db.Column(db.Integer, nullable=True, default=0)
    start_at = db.Column(db.DateTime, nullable=False)
    end_at = db.Column(db.DateTime, nullable=False)
    post_url = db.Column(db.String, nullable=True)
    status = db.Column(db.Integer, nullable=False, default=0)
    short_cut_url = db.Column(db.String, nullable=False)

class UserDetail(db.Model):
    __tablename__ = 'user_detail'

    id = db.Column(db.Integer, primary_key=True)
    open_id = db.Column(db.String, nullable=False)
    avatar_url = db.Column(db.String, nullable=False)
    city = db.Column(db.String, nullable=True)
    country = db.Column(db.String, nullable=True)
    gender = db.Column(db.String, nullable=True)
    language = db.Column(db.String, nullable=True)
    nickname = db.Column(db.String, nullable=False)
    birth_day = db.Column(db.Date, nullable=True)
    name = db.Column(db.String, nullable=True)
    phone_number = db.Column(db.String, nullable=True)
    register_at = db.Column(db.DateTime, nullable=False, default=datetime.now())
    register_from_id = db.Column(db.Integer, nullable=False, default=0)
    register_from_chn = db.Column(db.String, nullable=False, default="")


class ActOrders(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, nullable=False)
    act_id = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now())
    status = db.Column(db.Integer, nullable=False, default=0)
    amount = db.Column(db.Numeric(precision=10, scale=2, asdecimal=True), default=Decimal('0.00'), nullable=False)
    count = db.Column(db.Integer, nullable=False, default=1)
