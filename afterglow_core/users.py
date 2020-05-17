"""
Afterglow Core: user management
"""

import os
import time

from flask_sqlalchemy import SQLAlchemy
from flask_security import SQLAlchemyUserDatastore, UserMixin, RoleMixin

from . import app


__all__ = [
    'AnonymousUser', 'Role', 'User', 'Identity', 'PersistentToken',
    'UserClient', 'db', 'user_datastore',
]


app.config.setdefault(
    'SQLALCHEMY_DATABASE_URI', 'sqlite:///{}'.format(os.path.join(
        os.path.abspath(app.config['DATA_ROOT']), 'afterglow.db')))
app.config.setdefault('SQLALCHEMY_TRACK_MODIFICATIONS', False)

db = SQLAlchemy(app)
user_datastore = None

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
        db.CheckConstraint(
            'description is null or length(description) <= 255'))


class User(db.Model, UserMixin):
    __tablename__ = 'users'
    __table_args__ = dict(sqlite_autoincrement=True)

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(
        db.String,
        db.CheckConstraint('username is null or length(username) <= 255'),
        nullable=True, unique=True)
    password = db.Column(
        db.String,
        db.CheckConstraint('password is null or length(password) <= 255'))
    email = db.Column(
        db.String,
        db.CheckConstraint('email is null or length(email) <= 255'))
    first_name = db.Column(
        db.String,
        db.CheckConstraint(
            'first_name is null or length(first_name) <= 255'))
    last_name = db.Column(
        db.String,
        db.CheckConstraint('last_name is null or length(last_name) <= 255'))
    birth_date = db.Column(db.Date)
    active = db.Column(db.Boolean, server_default='1')
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    modified_at = db.Column(
        db.DateTime, default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp())
    roles = db.relationship(
        'Role', secondary=user_roles,
        backref=db.backref('users', lazy='dynamic'))
    settings = db.Column(
        db.String,
        db.CheckConstraint(
            'settings is null or length(settings) <= 1048576'),
        default='')

    @property
    def full_name(self):
        full_name = []
        if self.first_name:
            full_name.append(self.first_name)
        if self.last_name:
            full_name.append(self.last_name)
        return ' '.join(full_name)

    @property
    def display_name(self):
        if self.full_name:
            return self.full_name
        if self.email:
            return self.email
        return 'Anonymous'

    @property
    def is_admin(self):
        """Does the user have admin role?"""
        return Role.query.filter_by(name='admin').one() in self.roles

    def get_user_id(self):
        """Return user ID; required by authlib"""
        return self.id


class Identity(db.Model):
    __tablename__ = 'identities'
    __table_args__ = dict(sqlite_autoincrement=True)

    id = db.Column(db.Integer, primary_key=True, nullable=False)
    name = db.Column(
        db.String, db.CheckConstraint('length(name) <= 255'),
        nullable=False)
    user_id = db.Column(
        db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False)
    auth_method = db.Column(
        db.String,
        db.CheckConstraint('length(auth_method) <= 40'), nullable=False)
    data = db.Column(db.Text, default='')

    user = db.relationship(User, uselist=False, backref='identities')


class PersistentToken(db.Model):
    __tablename__ = 'tokens'
    __table_args__ = dict(sqlite_autoincrement=True)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False)
    token_type = db.Column(db.String(40), default='personal')
    access_token = db.Column(db.String(255), unique=True, nullable=False)
    issued_at = db.Column(
        db.Integer, nullable=False, default=lambda: int(time.time())
    )
    expires_in = db.Column(db.Integer, nullable=False, default=0)
    note = db.Column(db.Text, default='')

    user = db.relationship(User, uselist=False, backref='tokens')

    @property
    def active(self):
        if not self.expires_in:
            return True
        return self.issued_at + self.expires_in >= time.time()

    def get_expires_at(self):
        return self.issued_at + self.expires_in


# Need to place this here because OAuth2 clients are stored in the user
# database and initialized/migrated by Alembic along with the other
# user-related tables
class UserClient(db.Model):
    """
    List of clients allowed for the user; stored in the main Afterglow
    database
    """
    __tablename__ = 'user_oauth_clients'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False, index=True)
    user = db.relationship('User', uselist=False)
    client_id = db.Column(
        db.String, db.CheckConstraint('length(client_id) <= 40'),
        nullable=False, index=True)


class AnonymousUserRole(object):
    id = None
    name = 'user'
    description = 'Anonymous Afterglow User'


class AnonymousUser(object):
    id = None
    username = display_name = '<Anonymous>'
    first_name = None
    last_name = None
    full_name = ''
    email = ''
    password = ''
    birth_date = None
    active = True
    created_at = None
    modified_at = None
    roles = None
    identities = ()
    settings = ''
    is_admin = False

    def __init__(self):
        self.roles = (AnonymousUserRole(),)

    def get_user_id(self):
        """Return user ID; required by authlib"""
        return self.id


def _init_users():
    """Initialize Afterglow user datastore if AUTH_ENABLED = True"""
    # All imports put here to avoid unnecessary loading of packages on startup
    # if user auth is disabled
    try:
        from alembic import config as alembic_config, context as alembic_context
        from alembic.script import ScriptDirectory
        from alembic.runtime.environment import EnvironmentContext
    except ImportError:
        # noinspection PyPep8Naming
        ScriptDirectory = EnvironmentContext = None
        alembic_config = alembic_context = None

    global user_datastore

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
            os.path.abspath(os.path.join(
                __file__, '..', 'db_migration', 'users'))
        )
        script = ScriptDirectory.from_config(cfg)

        # noinspection PyProtectedMember
        with EnvironmentContext(
                cfg, script,
                fn=lambda rev, _: script._upgrade_revs('head', rev),
                as_sql=False, starting_rev=None, destination_rev='head',
                tag=None,
        ), db.engine.connect() as connection:
            alembic_context.configure(connection=connection)

            with alembic_context.begin_transaction():
                alembic_context.run_migrations()

    # Initialize user roles if missing
    try:
        roles_created = False
        for name, descr in [
                ('admin', 'Afterglow Administrator'),
                ('user', 'Afterglow User')]:
            if not user_datastore.find_role(name):
                user_datastore.create_role(name=name, description=descr)
                roles_created = True
        if roles_created:
            user_datastore.commit()
    except Exception:
        db.session.rollback()
        raise


if app.config.get('AUTH_ENABLED'):
    _init_users()
