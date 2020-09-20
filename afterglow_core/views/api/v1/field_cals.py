"""
Afterglow Core: API v1 field cal views
"""

from flask import request

from .... import app, auth, json_response
from ....resources.field_cals import SqlaFieldCal
from ....resources.data_files import get_data_file_db
from ....schemas.api.v1 import FieldCal
from ....errors import MissingFieldError
from ....errors.field_cal import UnknownFieldCalError, DuplicateFieldCalError
from . import url_prefix


resource_prefix = url_prefix + 'field-cals/'


@app.route(resource_prefix[:-1], methods=['GET', 'POST'])
@app.route(resource_prefix + '<id_or_name>', methods=['GET', 'PUT', 'DELETE'])
@auth.auth_required('user')
def field_cals(id_or_name=None):
    """
    Return, create, update, or delete field cal(s)

    GET /field-cals
        - return a list of all user's field cals

    GET /field-cals/[id or name]
        - return a single field cal with the given ID or name

    POST /field-cals?name=...
        - create field cal with the given name and parameters

    PUT /field-cals/[id or name]?...
        - update field cal parameters

    DELETE /field-cals/[id or name]
        - delete the given field cal

    :param str id_or_name: field cal ID (integer) or name

    :return:
        GET: JSON response containing either a list of serialized field cals
            when no ID/name supplied or a single field cal otherwise
        POST, PUT: JSON-serialized field cal
        DELETE: empty response
    :rtype: flask.Response | str
    """
    adb = get_data_file_db(auth.current_user.id)

    if id_or_name is not None:
        # When getting, updating, or deleting a field cal, check that it
        # exists
        try:
            field_cal = adb.query(SqlaFieldCal).get(int(id_or_name))
        except ValueError:
            field_cal = None
        if field_cal is None:
            # Try getting by name
            field_cal = adb.query(SqlaFieldCal).filter(
                SqlaFieldCal.name == id_or_name).one_or_none()
        if field_cal is None:
            raise UnknownFieldCalError(id=id_or_name)
    else:
        field_cal = None

    if request.method == 'GET':
        if id_or_name is None:
            # List all field cals
            return json_response(
                [FieldCal.from_db(field_cal)
                 for field_cal in adb.query(SqlaFieldCal)])

        # Return specific field cal resource
        return json_response(FieldCal.from_db(field_cal))

    if request.method == 'POST':
        # Create field cal
        if not request.args.get('name'):
            raise MissingFieldError(field='name')
        if adb.query(SqlaFieldCal).filter(
                SqlaFieldCal.name == request.args['name']).count():
            raise DuplicateFieldCalError(name=request.args['name'])
        try:
            field_cal = SqlaFieldCal(**request.args.to_dict())
            adb.add(field_cal)
            adb.flush()
            res = FieldCal.from_db(field_cal)
            adb.commit()
        except Exception:
            adb.rollback()
            raise

        return json_response(res, 201)

    if request.method == 'PUT':
        # Update field cal
        for key, val in request.args.items():
            if key == 'id':
                # Don't allow changing field cal ID
                continue
            if key == 'name' and val != field_cal.name and adb.query(
                    SqlaFieldCal).filter(SqlaFieldCal.name == val).count():
                raise DuplicateFieldCalError(name=val)
            setattr(field_cal, key, val)
        try:
            res = FieldCal.from_db(field_cal)
            adb.commit()
        except Exception:
            adb.rollback()
            raise

        return json_response(res)

    if request.method == 'DELETE':
        # Delete field cal
        try:
            adb.query(SqlaFieldCal).filter(
                SqlaFieldCal.id == field_cal.id).delete()
            adb.commit()
        except Exception:
            adb.rollback()
            raise

        return json_response()
