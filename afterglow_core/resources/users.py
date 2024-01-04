"""
Afterglow Core: user management
"""

import os
import time
import shutil
from datetime import datetime
from typing import List as TList, Optional, Union

from flask import Flask, current_app
from flask_sqlalchemy.model import Model
from flask_security import (
    Security, UserMixin, RoleMixin, SQLAlchemyUserDatastore)
from flask_security.utils import hash_password
from authlib.integrations.sqla_oauth2 import (
    OAuth2AuthorizationCodeMixin, OAuth2TokenMixin)
from sqlalchemy.orm import Mapped

from ..database import db
from ..models import User
from ..errors import MissingFieldError, ValidationError
from ..errors.auth import DuplicateUsernameError, UnknownUserError
from .base import DateTime, JSONType


__all__ = [
    'AnonymousUser', 'AnonymousUserRole',
    'DbIdentity', 'DbPersistentToken', 'DbRole', 'DbUser', 'DbUserClient',
    'db', 'user_datastore', 'init_users',
    'query_users', 'get_user', 'create_user', 'update_user', 'delete_user',
]


class AnonymousUserRole(object):
    id = None
    name = 'user'
    description = 'Anonymous Afterglow User'


class AnonymousUser(object):
    id = fs_uniquifier = None
    username = display_name = '<Anonymous>'
    first_name = None
    last_name = None
    full_name = ''
    email = ''
    password = ''
    active = True
    created_at = None
    modified_at = None
    roles: Union[Model, TList[AnonymousUserRole]] = None
    identities = ()
    settings = ''
    is_admin = False

    def __init__(self):
        self.roles = [AnonymousUserRole()]

    def get_user_id(self):
        """Return user ID; required by authlib"""
        return self.id


user_roles = db.Table(
    'user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id')),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id')))


class DbRole(db.Model, RoleMixin):
    __tablename__ = 'roles'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    name: Mapped[str] = db.Column(
        db.String, db.CheckConstraint('length(name) <= 80'), nullable=False,
        unique=True)
    description: Mapped[str] = db.Column(
        db.String,
        db.CheckConstraint(
            'description is null or length(description) <= 255'))


class DbUser(db.Model, UserMixin):
    __tablename__ = 'users'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    username: Mapped[str] = db.Column(
        db.String,
        db.CheckConstraint('username is null or length(username) <= 255'),
        nullable=True, unique=True)
    password: Mapped[str] = db.Column(
        db.String,
        db.CheckConstraint('password is null or length(password) <= 255'))
    email: Mapped[str] = db.Column(
        db.String,
        db.CheckConstraint('email is null or length(email) <= 255'))
    first_name: Mapped[str] = db.Column(
        db.String,
        db.CheckConstraint(
            'first_name is null or length(first_name) <= 255'))
    last_name: Mapped[str] = db.Column(
        db.String,
        db.CheckConstraint(
            'last_name is null or length(last_name) <= 255'))
    active: Mapped[bool] = db.Column(db.Boolean, server_default='1')
    created_at: Mapped[datetime] = db.Column(
        DateTime, default=db.func.current_timestamp())
    modified_at: Mapped[datetime] = db.Column(
        DateTime, default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp())
    roles: Mapped[TList['DbRole']] = db.relationship(
        secondary=user_roles,
        backref=db.backref('users', lazy='dynamic'))
    settings: Mapped[str] = db.Column(
        db.Text,
        db.CheckConstraint(
            'settings is null or length(settings) <= 1048576'), default='')

    identities: Mapped[TList['DbIdentity']] = db.relationship(
        back_populates='user')
    tokens: Mapped[TList['DbPersistentToken']] = db.relationship(
        back_populates='user')
    oauth_codes: Mapped[TList['OAuth2AuthorizationCode']] = db.relationship(
        back_populates='user')
    oauth_tokens: Mapped[TList['Token']] = db.relationship(
        back_populates='user')

    @property
    def full_name(self) -> str:
        full_name = []
        if self.first_name:
            full_name.append(self.first_name)
        if self.last_name:
            full_name.append(self.last_name)
        # noinspection PyTypeChecker
        return ' '.join(full_name)

    @property
    def display_name(self) -> str:
        if self.full_name:
            return self.full_name
        if self.email:
            # noinspection PyTypeChecker
            return self.email
        return 'Anonymous'

    @property
    def is_admin(self) -> bool:
        """Does the user have admin role?"""
        return DbRole.query.filter_by(name='admin').one() in self.roles

    @property
    def fs_uniquifier(self) -> int:
        """Return user ID; required by authlib"""
        return self.id


class DbIdentity(db.Model):
    __tablename__ = 'identities'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True, nullable=False)
    name: Mapped[str] = db.Column(
        db.String, db.CheckConstraint('length(name) <= 255'), nullable=False)
    user_id: Mapped[int] = db.Column(
        db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False)
    auth_method: Mapped[str] = db.Column(
        db.String,
        db.CheckConstraint('length(auth_method) <= 40'), nullable=False)
    data: Mapped[dict] = db.Column(JSONType, default={})

    user: Mapped['DbUser'] = db.relationship(back_populates='identities')


class DbPersistentToken(db.Model):
    __tablename__ = 'tokens'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    user_id: Mapped[int] = db.Column(
        db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False)
    token_type: Mapped[str] = db.Column(db.String(40), default='personal')
    access_token: Mapped[str] = db.Column(
        db.String(255), unique=True, nullable=False)
    issued_at: Mapped[int] = db.Column(
        db.Integer, nullable=False, default=lambda: int(time.time())
    )
    expires_in: Mapped[int] = db.Column(db.Integer, nullable=False, default=0)
    note: Mapped[str] = db.Column(db.Text, default='')

    user: Mapped['DbUser'] = db.relationship(back_populates='tokens')

    @property
    def active(self) -> bool:
        if not self.expires_in:
            return True
        return self.issued_at + self.expires_in >= time.time()

    def get_expires_at(self) -> int:
        return self.issued_at + self.expires_in


# Need to place this here because OAuth2 clients are stored in the user
# database and initialized/migrated by Alembic along with the other
# user-related tables
class DbUserClient(db.Model):
    """
    List of clients allowed for the user; stored in the main Afterglow
    database
    """
    __tablename__ = 'user_oauth_clients'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    user_id: Mapped[int] = db.Column(
        db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False, index=True)
    user: Mapped['DbUser'] = db.relationship()
    client_id: Mapped[str] = db.Column(
        db.String, db.CheckConstraint('length(client_id) <= 40'),
        nullable=False, index=True)


class OAuth2AuthorizationCode(db.Model, OAuth2AuthorizationCodeMixin):
    __tablename__ = 'oauth_codes'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    user_id: Mapped[int] = db.Column(
        db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False)

    user: Mapped['DbUser'] = db.relationship(back_populates='oauth_codes')


class Token(db.Model, OAuth2TokenMixin):
    """
    Token object; stored in the memory database
    """
    __tablename__ = 'oauth_tokens'

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    user_id: Mapped[int] = db.Column(
        db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False)
    # override Mixin to set default=oauth2
    token_type: Mapped[str] = db.Column(db.String(40), default='oauth2')
    note: Mapped[str] = db.Column(db.Text, default='')

    user: Mapped['DbUser'] = db.relationship(back_populates='oauth_tokens')

    @property
    def active(self) -> bool:
        return not self.is_revoked() and not self.is_expired()

    def is_refresh_token_active(self):
        if self.refresh_token_revoked_at:
            return False
        expires_at = self.issued_at + \
            current_app.config.get('REFRESH_TOKEN_EXPIRES')
        return expires_at >= time.time()


user_datastore = SQLAlchemyUserDatastore(db, DbUser, DbRole)


def init_users(app: Flask) -> None:
    """
    Initialize Afterglow user datastore if AUTH_ENABLED = True

    :param app: Flask application
    """
    # All imports put here to avoid unnecessary loading of packages on startup
    # if user auth is disabled
    from alembic import config as alembic_config, context as alembic_context
    from alembic.script import ScriptDirectory
    from alembic.runtime.environment import EnvironmentContext

    app.security = Security(app, user_datastore, register_blueprint=False)

    # Create/upgrade tables via Alembic
    cfg = alembic_config.Config()
    cfg.set_main_option('script_location', os.path.abspath(os.path.join(__file__, '../..', 'db_migration', 'users')))
    script = ScriptDirectory.from_config(cfg)

    # noinspection PyProtectedMember
    with EnvironmentContext(
            cfg, script, fn=lambda rev, _: script._upgrade_revs('head', rev), as_sql=False, starting_rev=None,
            destination_rev='head', tag=None), db.engine.connect() as connection:
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


def query_users(username: Optional[str] = None, active: Optional[str] = None,
                roles: Optional[str] = None) -> TList[User]:
    """
    Return users matching certain criteria; by default, return all users

    :param username: return users with matching username(s) (SQL ILIKE
        statement)
    :param active: return active (active`=1) or inactive (`active`=0) users
    :param roles: return users with the given role(s) (comma-separated)

    :return: list of user objects
    """
    try:
        q = DbUser.query
        if username:
            q = q.filter(DbUser.username.ilike(username.lower()))
        if active:
            try:
                active = bool(int(active))
            except ValueError:
                raise ValidationError('active', '"active" must be 0 or 1')
            q = q.filter_by(active=active)
        if roles:
            for role in roles.split(','):
                q = q.filter(DbUser.roles.any(DbRole.name == role))
        return [User(u) for u in q]
    except Exception:
        db.session.rollback()
        raise


def get_user(user_id: int) -> User:
    """
    Return user with the given ID

    :param user_id: user ID

    :return: user object
    """
    try:
        u = DbUser.query.get(user_id)
        if u is None:
            raise UnknownUserError(id=user_id)

        # Convert to data model object
        return User(u)
    except Exception:
        db.session.rollback()
        raise


def create_user(user: User) -> User:
    """
    Create a new user

    :param user: user object containing all relevant parameters

    :return: new user object
    """
    if not getattr(user, 'username'):
        raise MissingFieldError('username')
    if not getattr(user, 'password'):
        raise MissingFieldError('password')
    if getattr(user, 'active') is False:
        raise ValidationError('active', 'Cannot create inactive account')
    if DbUser.query.filter(
            db.func.lower(User.username) == user.username.lower()).count():
        raise DuplicateUsernameError(username=user.username)

    kw = user.to_dict()
    for name in ('id', 'identities'):
        try:
            del kw[name]
        except KeyError:
            pass
    kw['password'] = hash_password(kw['password'])
    kw['active'] = True
    if kw.get('roles'):
        role_objs = []
        for role in kw['roles'].split(','):
            r = DbRole.query.filter_by(name=role).one_or_none()
            if r is None:
                raise ValidationError(
                    'roles', 'Unknown role "{}"'.format(role))
            role_objs.append(r)
        kw['roles'] = role_objs
    else:
        kw['roles'] = []

    try:
        # noinspection PyArgumentList
        db_user = DbUser(**kw)
        db.session.add(db_user)
        db.session.flush()
        user = User(db_user)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return user


def update_user(user_id: int, user: User) -> User:
    """
    Update the existing user's profile

    :param user_id: user ID
    :param user: user object containing updated parameters

    :return: updated user object
    """
    try:
        db_user = DbUser.query.get(user_id)
        if db_user is None:
            raise UnknownUserError(id=user_id)

        for key, val in user.to_dict().items():
            if key == 'id':
                # Don't allow changing field cal ID
                continue
            if key == 'username' and val != db_user.username and \
                    DbUser.query.filter(
                        db.func.lower(User.username) == val.lower(),
                        User.id != user_id).count():
                raise DuplicateUsernameError(username=val)
            setattr(db_user, key, val)

        user = User(db_user)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return user


def delete_user(user_id: int) -> None:
    """
    Delete user with the given ID or name

    :param user_id: user ID
    """
    try:
        db_user = DbUser.query(user_id)
        if db_user is None:
            raise UnknownUserError(id=user_id)

        db_user.roles = []
        db.session.delete(db_user)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    else:
        data_file_dir = os.path.join(
            current_app.config['DATA_FILE_ROOT'], str(user_id))
        try:
            shutil.rmtree(data_file_dir)
        except Exception as exc:
            current_app.logger.warning(
                'Error removing user\'s data file directory "%s" '
                '[%s]', data_file_dir, user_id, exc)
