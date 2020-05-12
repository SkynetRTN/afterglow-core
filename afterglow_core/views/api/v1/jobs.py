#TODO remove unused imports

from . import url_prefix
from ....models.jobs import Job, JobResult, JobState, job_file_dir, job_file_path
from .... import (
    AfterglowSchemaEncoder, app, auth, json_response, plugins)
from ....errors import AfterglowError, MissingFieldError, ValidationError
from ....errors.job import (
    JobServerError, UnknownJobError, UnknownJobFileError, UnknownJobTypeError,
    InvalidMethodError, CannotSetJobStatusError, CannotCancelJobError,
    CannotDeleteJobError)
from ....resources.jobs import job_server_request


resource_prefix = url_prefix + 'jobs/'


@app.route(resource_prefix[:-1], methods=('GET', 'POST'))
@app.route(resource_prefix + '<int:id>', methods=('GET', 'DELETE'))
@auth.auth_required('user')
def jobs(id=None):
    """
    Return user's job(s), submit or delete a job

    GET /jobs?session_id=... -> [Job, Job...]
        - return a list of all user's jobs submitted from the given session
          (anonymous session by default)

    GET /jobs/[id] -> Job
        - return job with the given ID

    POST /jobs?type=...&session_id=...&... -> Job
        - submit a new job of the given type with the given job-specific
          parameters; if session_id is provided, the job is associated with
          the given client session

    DELETE /jobs/[id]
        - delete job with the given ID

    :param int id: job ID

    :return: JSON response
    :rtype: flask.Response
    """
    args = {}
    if id is not None:
        args['id'] = id
    return job_server_request('jobs', **args)


@app.route(resource_prefix + '<int:id>/state', methods=['GET', 'PUT'])
@auth.auth_required('user')
def jobs_state(id):
    """
    Return or modify job state

    GET /jobs/[id]/state -> JobState
        - get the current job state

    PUT /jobs/[id]/state?status=canceled -> JobState
        - cancel job

    :param int id: job ID

    :return: JSON response
    :rtype: flask.Response
    """
    return job_server_request('jobs/state', id=id)


@app.route(resource_prefix + '<int:id>/result')
@auth.auth_required('user')
def jobs_result(id):
    """
    Return job result

    GET /jobs/[id]/result -> JobResult

    :param int id: job ID

    :return: JSON response
    :rtype: flask.Response
    """
    return job_server_request('jobs/result', id=id)


@app.route(resource_prefix + '<int:id>/result/files/<file_id>')
@auth.auth_required('user')
def jobs_result_files(id, file_id):
    """
    Return extra job result file

    GET /jobs/[id]/result/files/[file_id] -> [binary data]

    :param int id: job ID
    :param str file_id: extra job result file ID

    :return: JSON response
    :rtype: flask.Response
    """
    return job_server_request('jobs/result/files', id=id, file_id=file_id)
