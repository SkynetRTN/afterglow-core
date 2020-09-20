"""
Afterglow Core: login and user account management routes
"""

import os
import shutil

from flask_security.utils import hash_password
from flask import request

from .... import app, json_response
from ....auth import auth_required
from ....users import Role, User, db
from ....schemas.api.v1 import UserSchema
from ....errors import MissingFieldError, ValidationError
from ....errors.auth import (
    AdminRequiredError, UnknownUserError, CannotDeactivateTheOnlyAdminError,
    DuplicateUsernameError, CannotDeleteCurrentUserError)
from . import url_prefix


def parse_user_fields():
    username = request.args.get('username')
    if username == '':
        raise ValidationError('username', 'Username cannot be empty')

    password = request.args.get('password')
    if password == '':
        raise ValidationError('password', 'Password cannot be empty')

    email = request.args.get('email')
    first_name = request.args.get('first_name')
    last_name = request.args.get('last_name')
    birth_date = request.args.get('birth_date')

    active = request.args.get('active')
    if active is not None:
        try:
            active = bool(int(active))
        except ValueError:
            raise ValidationError('active', '"active" must be 0 or 1')

    roles = request.args.get('roles')
    if roles is not None:
        role_objs = []
        for role in roles.split(','):
            r = Role.query.filter_by(name=role).one_or_none()
            if r is None:
                raise ValidationError('roles', 'Unknown role "{}"'.format(role))
            role_objs.append(r)
        roles = role_objs

    settings = request.args.get('settings')

    return (
        username, password, email, first_name, last_name, birth_date, active,
        roles, settings,
    )


@app.route(url_prefix + 'users', methods=['GET', 'POST'])
@app.route(url_prefix + 'users/<int:user_id>', methods=['GET', 'PUT', 'DELETE'])
@auth_required
def users(user_id: int = None):
    """
    List, create, and update user accounts

    GET /users
        - return the list of registered user IDs; non-admins get only
            their own ID

    GET /users?username=...&active=...&roles=...
        - return the list of IDs of registered users matching the given
            criteria; non-admins get only their own ID

    POST /users?username=...&password=...&roles=...&first_name=...&last_name=...
        &email=...&birth_date=...&settings=...
        - create a new user account; must be admin; roles may include
            "admin" and "user" (separated by comma if both)

    GET /users/[id]
        - return the given user info; must be admin or same user

    PUT /users/[id]?username=...&password=...&active=...&roles=...
        &first_name=...&last_name=...&email=...&birth_date=...&settings=...
        - update user account; must be admin or same user

    DELETE /users/[id]
        - delete the given user account; must be admin

    :params user_id: ID of the user to retrieve/update/delete

    :return: JSON or empty response
        GET: {"items"; [{user}, {user}, ...]}
        POST: {user}
        DELETE: empty response
    :rtype: flask.Response | str
    """
    # Admin rights are required for listing, creating, and deleting users;
    # not required for retrieving and updating the current user's profile
    if request.method not in ('GET', 'PUT') or user_id != request.user.id:
        if not request.user.is_admin:
            raise AdminRequiredError()

    # Request is authorized properly
    if request.method == 'GET' and user_id is None:
        # Return all users matching the given attributes
        q = User.query
        if request.args.get('username'):
            q = q.filter(User.username.ilike(request.args['username'].lower()))
        if request.args.get('active'):
            try:
                active = bool(int(request.args['active']))
            except ValueError:
                raise ValidationError('active', '"active" must be 0 or 1')
            q = q.filter(User.active == active)
        if request.args.get('roles'):
            for role in request.args['roles'].split(','):
                q = q.filter(User.roles.any(Role.name == role))

        return json_response({'items': UserSchema().dump(q.all(), many=True)})

    if request.method == 'POST':
        username, password, email, first_name, last_name, birth_date, active, \
            roles, settings = parse_user_fields()
        if username is None:
            raise MissingFieldError('username')
        if password is None:
            raise MissingFieldError('password')
        if active is not None and not active:
            raise ValidationError('active', 'Cannot create inactive account')
        if roles is None:
            roles = []

        if User.query.filter(
                db.func.lower(User.username) == username.lower()).count():
            raise DuplicateUsernameError(username=username)

        try:
            # noinspection PyArgumentList
            u = User(
                username=username,
                password=hash_password(password),
                email=email,
                first_name=first_name,
                last_name=last_name,
                birth_date=birth_date,
                active=True,
                roles=roles,
                settings=settings,
            )
            db.session.add(u)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        else:
            return json_response(UserSchema().dump(u), 201)

    # A /users/[id] request
    u = User.query.get(user_id)
    if u is None:
        raise UnknownUserError(id=user_id)

    if request.method == 'GET':
        return json_response(UserSchema().dump(u))

    # At least one active admin must remain when deactivating
    # admin account or removing admin role from account
    admin_role = Role.query.filter_by(name='admin').one()
    active_admins = admin_role.users.filter(User.active == True).count()

    if request.method == 'PUT':
        username, password, email, first_name, last_name, birth_date, active, \
            roles, settings = parse_user_fields()

        if username is not None and User.query.filter(
                db.func.lower(User.username) ==
                username.lower(), User.id != user_id).count():
            raise DuplicateUsernameError(username=username)

        if active is not None:
            if not request.user.is_admin:
                raise AdminRequiredError(
                    message='Must be admin to {} users'.format(
                        ('deactivate', 'activate')[active]))

            if active_admins < 2 and admin_role in u.roles and (
                    active is not None and not active or
                    roles is not None and admin_role not in roles):
                raise CannotDeactivateTheOnlyAdminError()

        try:
            if username is not None:
                u.username = username
            if password is not None:
                u.password = password
            if email is not None:
                u.email = email
            if first_name is not None:
                u.first_name = first_name
            if last_name is not None:
                u.last_name = first_name
            if birth_date is not None:
                u.birth_date = birth_date
            if active is not None:
                u.active = active
            if roles is not None:
                u.roles = roles
            if settings is not None:
                u.settings = settings

            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        else:
            return json_response(UserSchema().dump(u), 200)

    if request.method == 'DELETE':
        if u.id == request.user.id:
            raise CannotDeleteCurrentUserError()

        if active_admins < 2 and admin_role in u.roles:
            raise CannotDeactivateTheOnlyAdminError()

        try:
            u.roles = []
            db.session.delete(u)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        else:
            data_file_dir = os.path.join(
                app.config['DATA_FILE_ROOT'], str(u.id))
            try:
                shutil.rmtree(data_file_dir)
            except Exception as exc:
                app.logger.warn(
                    'Error removing user\'s data file directory "%s" '
                    '[%s]', data_file_dir, user_id, exc)
            return json_response()


# Aliases for logged in user
@app.route(url_prefix + 'user', methods=['GET', 'PUT'])
@auth_required
def current_user():
    return users(request.user.id)
