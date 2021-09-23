"""
Afterglow Core: login and user account management routes
"""

from flask import Response, request

from .... import app, json_response
from ....auth import auth_required
from ....models import User
from ....resources.users import *
from ....schemas.api.v1 import UserSchema
from ....errors.auth import (
    AdminOrSameUserRequiredError, AdminRequiredError,
    CannotDeactivateTheOnlyAdminError, CannotDeleteCurrentUserError)
from . import url_prefix


@app.route(url_prefix + 'users', methods=['GET', 'POST'])
@auth_required
def users() -> Response:
    """
    List or create user accounts; admins only

    GET /users
        - return a list of all registered users

    GET /users?username=...&active=...&roles=...
        - return the list of users matching the given criteria

    POST /users?username=...&password=...&roles=...&first_name=...
        &last_name=...&email=...&settings=...
        - create a new user account; roles may include "admin" and "user"
          (separated by comma if both)

    :return: JSON response
        GET: [{user}, {user}, ...]
        POST: {user}
    """
    if not request.user.is_admin:
        raise AdminRequiredError()

    if request.method == 'GET':
        # Return all users matching the given attributes
        return json_response(
            [UserSchema(u)
             for u in query_users(
                username=request.args.get('username'),
                active=request.args.get('active'),
                roles=request.args.get('roles'),
            )])

    if request.method == 'POST':
        # Create user
        return json_response(UserSchema(create_user(User(
            UserSchema(_set_defaults=True, **request.args.to_dict()),
            _set_defaults=True))), 201)


@app.route(url_prefix + 'users/<int:user_id>',
           methods=['GET', 'PUT', 'DELETE'])
@auth_required
def user(user_id: int) -> Response:
    """
    Get, update, or delete user account

    GET /users/[id]
        - return the given user info; must be admin or same user

    PUT /users/[id]?username=...&password=...&active=...&roles=...
        &first_name=...&last_name=...&email=...&settings=...
        - update user account; must be admin or same user; non-admin users
          cannot change "username", "active", and "roles"

    DELETE /users/[id]
        - delete the given user account; must be admin

    :param user_id: ID of the user to retrieve/update/delete

    :return: JSON or empty response
        GET, PUT: {user}
        DELETE: empty response
    """
    # Admin rights are required for listing, creating, and deleting users;
    # not required for retrieving and updating the current user's profile
    if not request.user.is_admin and user_id != request.user.id:
        raise AdminOrSameUserRequiredError()

    u = get_user(user_id)

    if request.method == 'GET':
        return json_response(UserSchema(u))

    # At least one active admin must remain when deactivating admin account
    # or removing admin role from account
    active_admins = len(query_users(roles='admin'))

    if request.method == 'PUT':
        u1 = User(UserSchema(**request.args.to_dict()),
                  only=list(request.args.keys()))

        if not request.user.is_admin:
            for attr in ('username', 'active', 'roles'):
                if getattr(u1, attr, None) is not None and \
                        getattr(u1, attr) != getattr(u, attr, None):
                    raise AdminRequiredError(
                        message='Must be admin to change User.{}'.format(attr))

        if getattr(u1, 'active', None) is not None:
            if active_admins < 2 and \
                    any(r.name == 'admin' for r in u.roles) and (
                    not u1.active or
                    getattr(u1, 'roles', None) is not None and
                    not any(r.name == 'admin' for r in u1.roles)):
                raise CannotDeactivateTheOnlyAdminError()

        u1 = update_user(u.id, u1)
        return json_response(UserSchema(u1))

    if request.method == 'DELETE':
        if u.id == request.user.id:
            raise CannotDeleteCurrentUserError()

        if active_admins < 2 and any(r.name == 'admin' for r in u.roles):
            raise CannotDeactivateTheOnlyAdminError()

        delete_user(u.id)

        return json_response()


# Aliases for logged in user
@app.route(url_prefix + 'user', methods=['GET', 'PUT'])
@auth_required
def current_user() -> Response:
    """
    Get or update the current user account info

    GET /user
        - return the current user info

    PUT /user?password=...&first_name=...&last_name=...&email=...&settings=...
        - update user account info; non-admin users cannot change "username",
          "active", and "roles"

    :return: current user info
    """
    return user(request.user.id)
