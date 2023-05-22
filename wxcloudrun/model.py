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
    __tablename__ = 'act_tetail'

    # 设定结构体对应表格的字段
    id = db.Column(db.Integer, primary_key=True)
    host_id = db.Column(db.Integer, nullable=False)
    loc = db.Column(db.text, nullable=False)
    name = db.Column(db.text, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    total_num = db.Column(db.Integer, nullable=False)
    cur_num = db.Column(db.Integer, nullable=True, default=0)
    start_at = db.Column(db.DateTime, nullable=False)
    end_at = db.Column(db.DateTime, nullable=False)
    post_url = db.Column(db.text, nullable=True)


class UserDetail(db.Model):
    __tablename__ = 'user_detail'
    id = db.Column(db.Integer, primary_key=True)
    open_id = db.Column(db.String, nullable=False)
    avatar_url = db.Column(db.String, nullable=False)
    sex = db.Column(db.String, nullable=True)
    age = db.Column(db.Integer, nullable=True)
    birth_day = db.Column(db.Date, nullable=True)
    name = db.Column(db.text, nullable=False)
