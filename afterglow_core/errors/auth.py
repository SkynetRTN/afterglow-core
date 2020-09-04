"""
Afterglow Core: authentication errors (subcodes 1xx)
"""

from . import AfterglowError


__all__ = [
    'AdminOrSameUserRequiredError', 'AdminRequiredError', 'AuthError',
    'CannotDeactivateTheOnlyAdminError', 'CannotDeleteCurrentUserError',
    'CannotSetProtectedUserDataError', 'DuplicateUsernameError',
    'HttpAuthFailedError', 'InactiveUserError', 'InitPageNotAvailableError',
    'LocalAccessRequiredError', 'NoAdminRegisteredError',
    'NotAuthenticatedError', 'NotInitializedError', 'UnknownAuthMethodError',
    'UnknownUserError', 'UnknownTokenError',
]


class AuthError(AfterglowError):
    """
    Base class for all Afterglow authentication errors
    """
    code = 403


class NotAuthenticatedError(AuthError):
    """
    User authentication failed, access denied

    Extra attributes::
        error_msg: authentication error message
    """
    code = 401
    subcode = 100
    message = 'Not authenticated'


class NoAdminRegisteredError(AuthError):
    """
    Attempt to manage users (except for adding admin during the initial setup)
    with no admins registered in the system

    Extra attributes::
        None
    """
    subcode = 101
    message = 'No admins registered'


class AdminRequiredError(AuthError):
    """
    Request needs authentication with admin role

    Extra attributes::
        None
    """
    subcode = 102
    message = 'Must be admin to do that'


class AdminOrSameUserRequiredError(AuthError):
    """
    Request needs authentication with admin role or the same user it refers to

    Extra attributes::
        None
    """
    subcode = 103
    message = 'Must be admin or same user to do that'


class UnknownUserError(AuthError):
    """
    User with the given ID is not registered

    Extra attributes::
        id: user ID
    """
    code = 404
    subcode = 104
    message = 'Unknown user'


class InactiveUserError(AfterglowError):
    """
    Attempting to access Afterglow using an inactive user account

    Extra attributes::
        None
    """
    subcode = 105
    message = 'The user is deactivated'


class CannotDeactivateTheOnlyAdminError(AuthError):
    """
    Deactivating, removing admin role, or deleting the only admin user
    in the system

    Extra attributes::
        None
    """
    subcode = 106
    message = 'Cannot deactivate/delete the only admin in the system'


class DuplicateUsernameError(AuthError):
    """
    Attempting to register user with username that is already associated with
    some other user

    Extra attributes::
        username: duplicate username
    """
    subcode = 107
    message = 'User with this username already exists'


class UnknownAuthMethodError(AuthError):
    """
    Auth method was requested that is not registered in USER_AUTH

    Extra attributes::
        method: auth method ID
    """
    code = 404
    subcode = 108
    message = 'Unknown authentication method'


class CannotSetProtectedUserDataError(AfterglowError):
    """
    The user is trying to update protected info

    Extra attributes::
        attr: read-only user attribute
    """
    subcode = 109
    message = 'Cannot modify protected user info'


class HttpAuthFailedError(AuthError):
    """
    HTTP authentication data (username/password or Authentication-Token header)
    missing or invalid

    Extra attributes::
        None
    """
    code = 401
    subcode = 110
    message = 'Invalid or missing username/password or authentication token'
    # Causes browsers to pop-up login form upon failed login attempt
    # headers = [
    #     ('WWW-Authenticate',
    #      'Basic realm="{}"'.format('Local Afterglow Users Only'))]


class CannotDeleteCurrentUserError(AuthError):
    """
    Deleting currently authenticated user

    Extra attributes::
        None
    """
    subcode = 111
    message = 'Cannot delete the currently authenticated user'


class LocalAccessRequiredError(AuthError):
    """
    Only requests from localhost allowed

    Extra attributes::
        None
    """
    subcode = 112
    message = 'Must be local to do that'


class InitPageNotAvailableError(AuthError):
    """
    Afterglow Core has already been initialized

    Extra attributes::
        None
    """
    subcode = 113
    message = 'Afterglow Core has already been initialized'


class NotInitializedError(AuthError):
    """
    Afterglow core has not yet been initialized

    Extra attributes::
        None
    """
    subcode = 114
    message = 'Afterglow Core has not yet been initialized'


class UnknownTokenError(AfterglowError):
    """
    DELETEing /users/tokens/<id> with invalid id

    Extra attributes::
        None
    """
    code = 400
    subcode = 115
    message = 'Unknown token error'
