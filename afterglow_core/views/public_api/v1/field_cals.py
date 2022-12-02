"""
Afterglow Core: API v1 field cal views
"""

from flask import Blueprint, Flask, Response, request

from .... import auth, json_response
from ....models import FieldCal
from ....resources.field_cals import *
from ....schemas.api.v1 import FieldCalSchema
from . import url_prefix


__all__ = ['register']


blp = Blueprint('field_cals', __name__, url_prefix=url_prefix + 'field-cals')


def register(app: Flask) -> None:
    """
    Register endpoints

    :param app: Flask application
    """
    app.register_blueprint(blp)


@blp.route('/', methods=['GET', 'POST'])
@auth.auth_required('user')
def field_cals() -> Response:
    """
    Return or create field cal(s)

    GET /field-cals
        - return a list of all user's field cals

    POST /field-cals?name=...
        - create field cal with the given name and parameters

    :return:
        GET: JSON response containing a list of serialized field cals
        POST: JSON-serialized field cal
    """
    if request.method == 'GET':
        # List all field cals
        return json_response(
            [FieldCalSchema(cal)
             for cal in query_field_cals(request.user.id)])

    if request.method == 'POST':
        # Create field cal
        return json_response(FieldCalSchema(create_field_cal(
            request.user.id,
            FieldCal(FieldCalSchema(**request.args.to_dict()),
                     only=list(request.args.keys())))), 201)


@blp.route('/<id_or_name>', methods=['GET', 'PUT', 'DELETE'])
@auth.auth_required('user')
def field_cal(id_or_name: str) -> Response:
    """
    Return, update, or delete a field cal

    GET /field-cals/[id or name]
        - return a single field cal with the given ID or name

    PUT /field-cals/[id or name]?...
        - update field cal parameters

    DELETE /field-cals/[id or name]
        - delete the given field cal

    :param id_or_name: field cal ID (integer) or name

    :return:
        GET, PUT: JSON-serialized field cal
        DELETE: empty response
    """
    cal = get_field_cal(request.user.id, id_or_name)

    if request.method == 'GET':
        # Return specific field cal resource
        return json_response(FieldCalSchema(cal))

    if request.method == 'PUT':
        # Update field cal
        return json_response(FieldCalSchema(update_field_cal(
            request.user.id, cal.id,
            FieldCal(FieldCalSchema(**request.args.to_dict()),
                     only=list(request.args.keys())))))

    if request.method == 'DELETE':
        # Delete field cal
        delete_field_cal(request.user.id, cal.id)
        return json_response()
