"""
Afterglow Access Server: user management
"""

from __future__ import absolute_import, division, print_function

import os
from datetime import datetime
from marshmallow import Schema, fields
from flask_sqlalchemy import SQLAlchemy
from flask_security import SQLAlchemyUserDatastore, UserMixin, RoleMixin

from . import app

try:
    # noinspection PyUnresolvedReferences
    from alembic import config as alembic_config, context as alembic_context
    from alembic.script import ScriptDirectory
    from alembic.runtime.environment import EnvironmentContext
except ImportError:
    ScriptDirectory = EnvironmentContext = None
    alembic_config = alembic_context = None


__all__ = [
    'AnonymousUser', 'Role', 'RoleSchema', 'User', 'UserSchema', 'UserClient',
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
    name = db.Column(
        db.String, db.CheckConstraint('length(name) <= 80'), nullable=False,
        unique=True)
    description = db.Column(
        db.String,
        db.CheckConstraint('description is null or length(description) <= 255'))


# noinspection PyClassHasNoInit
class RoleSchema(Schema):
    id = fields.Integer()  # type: int
    name = fields.String()  # type: str
    description = fields.String()  # type: str


class User(db.Model, UserMixin):
    __tablename__ = 'users'
    __table_args__ = dict(sqlite_autoincrement=True)

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(
        db.String,
        db.CheckConstraint('username is null or length(username) <= 255'))
    alias = db.Column(
        db.String,
        db.CheckConstraint('alias is null or length(email) <= 255'))
    email = db.Column(
        db.String,
        db.CheckConstraint('email is null or length(email) <= 255'))
    password = db.Column(
        db.String,
        db.CheckConstraint('password is null or length(password) <= 255'))
    first_name = db.Column(
        db.String,
        db.CheckConstraint('first_name is null or length(first_name) <= 255'))
    last_name = db.Column(
        db.String,
        db.CheckConstraint('last_name is null or length(last_name) <= 255'))
    active = db.Column(db.Boolean, server_default='1')
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    modified_at = db.Column(
        db.DateTime, default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp())
    roles = db.relationship(
        'Role', secondary=user_roles,
        backref=db.backref('users', lazy='dynamic'))
    auth_methods = db.Column(
        db.String,
        db.CheckConstraint(
            'auth_methods is null or length(auth_methods) <= 255'),
        default='')
    settings = db.Column(
        db.String,
        db.CheckConstraint('settings is null or length(settings) <= 1048576'),
        default='')

    @property
    def full_name(self):
        full_name = []
        if self.first_name: full_name.append(self.first_name)
        if self.last_name: full_name.append(self.last_name)
        return ' '.join(full_name)

    @property
    def display_name(self):
        if self.full_name: return self.full_name
        if self.username: return self.username
        if self.alias: return self.alias
        if self.email: return self.email
        return "Anonymous"
        

    @property
    def is_admin(self):
        """Does the user have admin role?"""
        return Role.query.filter_by(name='admin').one() in self.roles

    def get_user_id(self):
        """Return user ID; required by authlib"""
        return self.id


# noinspection PyClassHasNoInit
class UserSchema(Schema):
    id = fields.Integer()  # type: int
    username = fields.String()  # type: str
    email = fields.String()  # type: str
    first_name = fields.String()  # type: str
    last_name = fields.String()  # type: str
    active = fields.Boolean()  # type: bool
    created_at = fields.DateTime()  # type: datetime
    modified_at = fields.DateTime()  # type: datetime
    roles = fields.List(fields.Nested(RoleSchema, only=['name']))  # type: list
    settings = fields.String()  # type: str


# Need to place this here because OAuth2 clients are stored in the user database
# and initialized/migrated by Alembic along with the other user-related tables
class UserClient(db.Model):
    """
    List of clients allowed for the user; stored in the main Afterglow database
    """
    __tablename__ = 'user_oauth_clients'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False, index=True)
    user = db.relationship('User')
    client_id = db.Column(
        db.String, db.CheckConstraint('length(client_id) <= 40'),
        nullable=False, index=True)


user_datastore = SQLAlchemyUserDatastore(db, User, Role)

# Create data_files table
if alembic_config is None:
    # Alembic not available, create table from SQLA metadata
    db.create_all()
else:
    # Create/upgrade tables via Alembic
    cfg = alembic_config.Config()
    cfg.set_main_option(
        'script_location',
        os.path.abspath(os.path.join(__file__, '..', 'db_migration', 'users'))
    )
    script = ScriptDirectory.from_config(cfg)

    # noinspection PyProtectedMember
    with EnvironmentContext(
            cfg, script, fn=lambda rev, _:
            script._upgrade_revs('head', rev),
            as_sql=False, starting_rev=None,
            destination_rev='head', tag=None,
    ), db.engine.connect() as connection:
        alembic_context.configure(connection=connection)

        with alembic_context.begin_transaction():
            alembic_context.run_migrations()

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


class AnonymousUserRole(object):
    id = None
    name = 'user'
    description = 'Anonymous Afterglow Access User'


class AnonymousUser(object):
    id = None
    username = '<Anonymous>'
    email = ''
    password = ''
    active = True
    created_at = None
    modified_at = None
    roles = None
    auth_methods = None
    settings = ''
    is_admin = False

    def __init__(self):
        self.roles = (AnonymousUserRole(),)

    def get_user_id(self):
        """Return user ID; required by authlib"""
        return self.id

