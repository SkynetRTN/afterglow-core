"""
Afterglow Access Server: user management
"""

from __future__ import absolute_import, division, print_function

import os
from marshmallow import Schema, fields
from flask_sqlalchemy import SQLAlchemy
from flask_security import SQLAlchemyUserDatastore, UserMixin, RoleMixin

from . import app


__all__ = [
    'AnonymousUser', 'Role', 'RoleSchema', 'User', 'UserSchema',
    'db', 'user_datastore',
]


app.config.setdefault(
    'SQLALCHEMY_DATABASE_URI', 'sqlite:///{}'.format(os.path.join(
        os.path.abspath(app.config['DATA_ROOT']), 'afterglow.db')))
app.config.setdefault('SQLALCHEMY_TRACK_MODIFICATIONS', False)
db = SQLAlchemy(app)

user_roles = db.Table(
    'user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id')),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id')))


class Role(db.Model, RoleMixin):
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))


# noinspection PyClassHasNoInit
class RoleSchema(Schema):
    id = fields.Integer()
    name = fields.String()
    description = fields.String()


class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True)
    email = db.Column(db.String(255))
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean, server_default='1')
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    modified_at = db.Column(
        db.DateTime, default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp())
    roles = db.relationship(
        'Role', secondary=user_roles,
        backref=db.backref('users', lazy='dynamic'))
    auth_methods = db.Column(db.String(255), default='')


# noinspection PyClassHasNoInit
class UserSchema(Schema):
    id = fields.Integer()
    username = fields.String()
    email = fields.String()
    active = fields.Boolean()
    created_at = fields.DateTime()
    modified_at = fields.DateTime()
    roles = fields.List(fields.Nested(RoleSchema, only=['name']))


user_datastore = SQLAlchemyUserDatastore(db, User, Role)

db.create_all()

# Initialize user roles if missing
try:
    roles_created = False
    for name, descr in [
            ('admin', 'Afterglow Access Server Administrator'),
            ('user', 'Afterglow Access User')]:
        if not user_datastore.find_role(name):
            user_datastore.create_role(name=name, description=descr)
            roles_created = True
    if roles_created:
        user_datastore.commit()
except Exception:
    db.session.rollback()
    raise


class AnonymousUser(User):
    id = None
    username = '<Anonymous>'
    password = ''
    active = True
    created_at = None
    modified_at = None
    roles = (Role.query.filter_by(name='user').one(),)
