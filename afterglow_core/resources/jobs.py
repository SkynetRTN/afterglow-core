"""
Afterglow Core: job resources

Job types are defined in afterglow_core.job_plugins.
"""

import pickle
import struct
import socket
from typing import Any, Dict as TDict

from .. import app
from ..errors import AfterglowError
from ..errors.job import JobServerError
from ..job_server import msg_hdr, msg_hdr_size


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
    try:
        # Prepare server message
        msg = dict(args)
        msg.update(dict(
            resource=resource,
            method=method,
            user_id=getattr(auth.current_user, 'id', None),
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
