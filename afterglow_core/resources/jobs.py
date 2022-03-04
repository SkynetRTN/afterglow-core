"""
Afterglow Core: job resources

Job types are defined in afterglow_core.job_plugins.
"""

import pickle
import socket
import struct
import sys
import traceback
from typing import Any, Dict as TDict

from werkzeug.http import HTTP_STATUS_CODES

from .. import app
from ..errors import AfterglowError, MissingFieldError
from ..errors.job import JobServerError, UnknownJobError
from ..job_server import DbJob, job_types, msg_hdr, msg_hdr_size


__all__ = ['job_server_request']


def job_server_request(resource: str, method: str, **args) -> TDict[str, Any]:
    """
    Make a request to job server and return response

    :param resource: resource ID: "jobs", "jobs/state", "jobs/result",
        "jobs/result/files"
    :param method: request method: "get", "post", "put", or "delete"
    :param args: extra request-specific arguments

    :return: response message
    """
    from .. import auth
    user_id = getattr(auth.current_user, 'id', None)

    if resource == 'jobs/result' and method.lower() == 'get' and \
            app.config.get('DB_BACKEND', 'sqlite') != 'sqlite':
        # Fast path for getting job result when using non-sqlite backends:
        # retrieve job result directly from the database to avoid extra
        # serialization of large data
        # Return job result
        from .users import db
        try:
            try:
                job_id = args['id']
            except KeyError:
                raise MissingFieldError(field='id')

            db_job = db.session.query(DbJob).get(job_id)
            if db_job is None or db_job.user_id != user_id:
                raise UnknownJobError(id=job_id)

            # Deduce the polymorphic job result type from the parent
            # job model; add job type info for the /jobs/[id]/result
            # view to be able to find the appropriate schema as well
            result = job_types[db_job.type].fields['result'].nested(
                db_job.result).to_dict()
            result['type'] = db_job.type
            http_status = 200

        except AfterglowError as e:
            # Construct JSON error response in the same way as
            # errors.afterglow_error_handler()
            http_status = int(getattr(e, 'code', 0)) or 400
            result = {
                'status': HTTP_STATUS_CODES.get(
                    http_status, '{} Unknown Error'.format(http_status)),
                'id': str(getattr(e, 'id', e.__class__.__name__)),
                'detail': str(e),
            }
            meta = getattr(e, 'meta', None)
            if meta:
                result['meta'] = dict(meta)
            if http_status == 500:
                result.setdefault('meta', {})['traceback'] = \
                    traceback.format_tb(sys.exc_info()[-1]),

        except Exception as e:
            # Wrap other exceptions in JobServerError
            # noinspection PyUnresolvedReferences
            http_status = JobServerError.code
            result = {
                'status': HTTP_STATUS_CODES[http_status],
                'id': e.__class__.__name__,
                'detail': str(e),
                'meta': {'traceback': traceback.format_tb(sys.exc_info()[-1])},
            }

        return {'json': result, 'status': http_status}

    try:
        # Prepare server message
        msg = dict(args)
        msg.update(dict(
            resource=resource,
            method=method,
            user_id=user_id,
        ))
        msg = pickle.dumps(msg)

        # Send message
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('localhost', app.config['JOB_SERVER_PORT']))
        try:
            sock.sendall(struct.pack(msg_hdr, len(msg)) + msg)

            # Get response
            msg_len = bytearray()
            while len(msg_len) < msg_hdr_size:
                msg_len += sock.recv(msg_hdr_size - len(msg_len))
            msg_len = struct.unpack(msg_hdr, msg_len)[0]

            msg = bytearray()
            while len(msg) < msg_len:
                msg += sock.recv(msg_len - len(msg))
        finally:
            # sock.shutdown(socket.SHUT_RDWR)
            sock.close()
    except AfterglowError:
        raise
    except Exception as e:
        # noinspection PyUnresolvedReferences
        raise JobServerError(
            reason=e.message if hasattr(e, 'message') and e.message
            else ', '.join(str(arg) for arg in e.args) if e.args else str(e))

    try:
        msg = pickle.loads(msg)
        if not isinstance(msg, dict):
            raise Exception()
    except Exception:
        raise JobServerError(reason='A dict expected')

    return msg
