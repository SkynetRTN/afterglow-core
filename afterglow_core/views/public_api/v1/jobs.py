"""
Afterglow Core: API v1 job views
"""

from typing import Any, Dict as TDict

from flask import Blueprint, Flask, Response, request, send_file

from .... import auth, json_response
from ....job_server import job_server_request
from ....schemas.api.v1 import JobSchema, JobStateSchema
from . import url_prefix


__all__ = ['register']


blp = Blueprint('jobs', __name__, url_prefix=url_prefix + 'jobs')


def register(app: Flask) -> None:
    """
    Register endpoints

    :param app: Flask application
    """
    app.register_blueprint(blp)


def error_response(msg: TDict[str, Any]) -> Response:
    """
    Return Flask error response if HTTP status code in the message
    is not as expected

    :param msg: job server message returned by :func:`job_server_request`

    :return: Flask response
    """
    return json_response(
        msg.get('json', '"<MISSING ERROR MESSAGE>"'), msg['status'],
        headers=msg.get('headers'))


@blp.route('/', methods=('GET', 'POST'))
@auth.auth_required('user')
def jobs() -> Response:
    """
    Return user's jobs or submit a job

    GET /jobs?session_id=... -> [Job, Job...]
        - return a list of all user's jobs submitted from the given session
          (anonymous session by default)

    POST /jobs?type=...&session_id=...&... -> Job
        - submit a new job of the given type with the given job-specific
          parameters; if session_id is provided, the job is associated with
          the given client session

    :return:
        GET: list of serialized job objects
        POST: serialized new job object
    """
    method = request.method
    if method == 'GET':
        # Return all user's jobs, optionally for the given session only
        args = {}
        if 'session_id' in request.args:
            args['session_id'] = request.args['session_id']
        msg = job_server_request('jobs', method, **args)
        if msg['status'] != 200:
            return error_response(msg)
        return json_response([JobSchema(exclude=['state', 'result'], **j) for j in msg['json']])

    if method == 'POST':
        # Submit a job
        msg = job_server_request(
            'jobs', method, **JobSchema(exclude=['state', 'result'], **request.args.to_dict()).to_dict())
        if msg['status'] != 201:
            return error_response(msg)
        return json_response(JobSchema(exclude=['state', 'result'], **msg['json']))


@blp.route('/<id>', methods=('GET', 'DELETE'))
@auth.auth_required('user')
def job(id: str) -> Response:
    """
    Return or delete user's job

    GET /jobs/[id] -> Job
        - return job with the given ID

    DELETE /jobs/[id]
        - delete job with the given ID

    :param id: job ID

    :return:
        GET: serialized job structure
        DELETE: empty response
    """
    # Return/delete job with the given ID
    method = request.method
    msg = job_server_request('jobs', method, id=id)
    if method == 'GET' and msg['status'] != 200 or \
            method == 'DELETE' and msg['status'] != 204:
        return error_response(msg)
    if method == 'GET':
        return json_response(JobSchema(exclude=['state', 'result'], **msg['json']))
    if method == 'DELETE':
        return json_response()


@blp.route('/<id>/state', methods=['GET', 'PUT'])
@auth.auth_required('user')
def jobs_state(id: str) -> Response:
    """
    Return or modify job state

    GET /jobs/[id]/state -> JobState
        - get the current job state

    PUT /jobs/[id]/state?status=canceled -> JobState
        - cancel job

    :param id: job ID

    :return: serialized job state structure
    """
    method = request.method
    if method == 'GET':
        # Return job state
        msg = job_server_request('jobs/state', method, id=id)
    else:
        # Update job state
        args = {}
        if 'status' in request.args:
            args['status'] = request.args['status']
        msg = job_server_request('jobs/state', method, id=id, **args)

    if msg['status'] != 200:
        return error_response(msg)
    return json_response(JobStateSchema(**msg['json']))


@blp.route('/<id>/result')
@auth.auth_required('user')
def jobs_result(id: str) -> Response:
    """
    Return job result

    GET /jobs/[id]/result -> JobResult

    :param id: job ID

    :return: serialized job result structure
    """
    msg = job_server_request('jobs/result', 'GET', id=id)
    if msg['status'] != 200:
        return error_response(msg)

    # Find the appropriate job result type from the job schema's "result" field
    job_type = msg['json'].pop('type')
    job_schema = JobSchema
    for j in JobSchema.__subclasses__():
        if j.type == job_type:
            job_schema = j
            break
    return json_response(
        job_schema().fields['result'].nested(**msg['json']))


@blp.route('/<id>/result/files/<file_id>')
@auth.auth_required('user')
def jobs_result_files(id: str, file_id: str) -> Response:
    """
    Return extra job result file

    GET /jobs/[id]/result/files/[file_id] -> [binary data]

    :param id: job ID
    :param file_id: extra job result file ID

    :return: binary data in the response body with the appropriate MIME type
    """
    msg = job_server_request(
        'jobs/result/files', 'GET', id=id, file_id=file_id)
    if msg['status'] != 200:
        return error_response(msg)
    return send_file(
        msg['json']['filename'],
        msg['json']['mimetype'] or 'application/octet-stream')
