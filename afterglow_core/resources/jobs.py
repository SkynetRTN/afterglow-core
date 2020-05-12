#remove 
"""
Afterglow Core: job resources

Job types are defined in afterglow_core.job_plugins.
"""

from __future__ import absolute_import, division, print_function

import sys
import os
import traceback
import shutil
import errno
import ctypes
import signal
import json
import struct
import socket
import cProfile
from datetime import datetime
from glob import glob
from multiprocessing import Event, Process, Queue
import threading
import sqlite3

# noinspection PyProtectedMember
from marshmallow import (
    Schema, fields, missing, __version_info__ as marshmallow_version)
from sqlalchemy import (
    Boolean, Column, Float, ForeignKey, Integer, String, Text, create_engine,
    event, text, types)
# noinspection PyProtectedMember
from sqlalchemy.engine import Engine
from sqlalchemy.orm import relationship, scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import TypeDecorator
from flask import Response, request

from ..models.jobs import Job, JobResult, JobState, job_file_dir, job_file_path
from .. import (
    AfterglowSchemaEncoder, app, auth, json_response, plugins)
from ..errors import AfterglowError, MissingFieldError, ValidationError
from ..errors.job import (
    JobServerError, UnknownJobError, UnknownJobFileError, UnknownJobTypeError,
    InvalidMethodError, CannotSetJobStatusError, CannotCancelJobError,
    CannotDeleteJobError)
from .data_files import SqlaSession, get_data_file_db

if sys.version_info.major < 3:
    # noinspection PyUnresolvedReferences,PyCompatibility
    from SocketServer import BaseRequestHandler, ThreadingTCPServer
else:
    # noinspection PyUnresolvedReferences,PyCompatibility
    from socketserver import BaseRequestHandler, ThreadingTCPServer

    # noinspection PyShadowingBuiltins
    unicode = str

# Encryption imports
try:
    # Try pycryptodomex first
    from Cryptodome import Random
    from Cryptodome.Cipher import AES
except ImportError:
    # Fall back to pycryptodome
    try:
        # noinspection PyProtectedMember
        from Crypto import Random, __version__
        from Crypto.Cipher import AES
        if int(__version__.split('.')[0]) < 3:
            # This is actually pycrypto, which is not supported
            Random = AES = None
        del __version__
    except (ImportError, AttributeError):
        Random = AES = None


__all__ = []


# Read/write lock by Fazal Majid
# (http://www.majid.info/mylos/weblog/2004/11/04-1.html)
# updated to support context manager protocol
class RWLock(object):
    """
    A simple reader-writer lock Several readers can hold the lock
    simultaneously, XOR one writer. Write locks have priority over reads to
    prevent write starvation.
    """
    def __init__(self):
        self.rwlock = 0
        self.writers_waiting = 0
        self.monitor = threading.Lock()
        self.readers_ok = threading.Condition(self.monitor)
        self.writers_ok = threading.Condition(self.monitor)

    def acquire_read(self):
        """
        Acquire a read lock. Several threads can hold this typeof lock.
        It is exclusive with write locks.
        """
        self.monitor.acquire()
        while self.rwlock < 0 or self.writers_waiting:
            self.readers_ok.wait()
        self.rwlock += 1
        self.monitor.release()
        return self

    def acquire_write(self):
        """
        Acquire a write lock. Only one thread can hold this lock, and
        only when no read locks are also held.
        """
        self.monitor.acquire()
        while self.rwlock != 0:
            self.writers_waiting += 1
            self.writers_ok.wait()
            self.writers_waiting -= 1
        self.rwlock = -1
        self.monitor.release()
        return self

    def promote(self):
        """
        Promote an already-acquired read lock to a write lock
        WARNING: it is very easy to deadlock with this method
        """
        self.monitor.acquire()
        self.rwlock -= 1
        while self.rwlock != 0:
            self.writers_waiting += 1
            self.writers_ok.wait()
            self.writers_waiting -= 1
        self.rwlock = -1
        self.monitor.release()

    def demote(self):
        """
        Demote an already-acquired write lock to a read lock
        """
        self.monitor.acquire()
        self.rwlock = 1
        self.readers_ok.notifyAll()
        self.monitor.release()

    def release(self):
        """
        Release a lock, whether read or write.
        """
        self.monitor.acquire()
        if self.rwlock < 0:
            self.rwlock = 0
        else:
            self.rwlock -= 1
        wake_writers = self.writers_waiting and self.rwlock == 0
        wake_readers = self.writers_waiting == 0
        self.monitor.release()
        if wake_writers:
            self.writers_ok.acquire()
            self.writers_ok.notify()
            self.writers_ok.release()
        elif wake_readers:
            self.readers_ok.acquire()
            self.readers_ok.notifyAll()
            self.readers_ok.release()

    def __enter__(self):
        """
        Context manager protocol support, called after acquiring the lock on
        either read or write

        :return: None
        """
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager protocol support, called after acquiring the lock on
        either read or write

        :return: False if exception is raised within the "with" block
        :rtype: bool
        """
        self.release()
        return exc_type is None


# Load job plugins
job_types = plugins.load_plugins('job', 'resources.job_plugins', Job)


Base = declarative_base()


# noinspection PyAbstractClass
class JSONType(TypeDecorator):
    """
    Text column that contains a JSON data structure; a simplified version of
    :class:`sqlalchemy_utils.types.json.JSONType`
    """
    impl = types.UnicodeText

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = unicode(json.dumps(value, cls=AfterglowSchemaEncoder))
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value


# noinspection PyAbstractClass
class DateTime(TypeDecorator):
    """
    DateTime column that can be assigned an ISO-formatted string
    """
    impl = types.DateTime

    def process_bind_param(self, value, dialect):
        if value is not None and not isinstance(value, datetime):
            value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S.%f')
        return value


# noinspection PyAbstractClass
class Date(TypeDecorator):
    """
    Date column that can be assigned an ISO-formatted string
    """
    impl = types.Date

    def process_bind_param(self, value, dialect):
        if isinstance(value, datetime):
            value = value.date()
        elif value is not None and not isinstance(value, datetime):
            value = datetime.strptime(value, '%Y-%m-%d')
        return value


# noinspection PyAbstractClass
class Time(TypeDecorator):
    """
    Time column that can be assigned an ISO-formatted string
    """
    impl = types.Time

    def process_bind_param(self, value, dialect):
        if isinstance(value, datetime):
            value = value.time()
        elif value is not None and not isinstance(value, datetime):
            value = datetime.strptime(value, '%H:%M:%S.%f')
        return value


class DbJobState(Base):
    __tablename__ = 'job_states'

    id = Column(
        ForeignKey('jobs.id', ondelete='CASCADE'), index=True, primary_key=True)
    status = Column(String(16), nullable=False, index=True, default='pending')
    created_on = Column(
        DateTime, nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    completed_on = Column(DateTime)
    progress = Column(Float, nullable=False, default=0)


class DbJobResult(Base):
    __tablename__ = 'job_results'

    id = Column(
        ForeignKey('jobs.id', ondelete='CASCADE'), index=True, primary_key=True)
    type = Column(String(40), index=True)
    errors = Column(JSONType, nullable=False, default=[])
    warnings = Column(JSONType, nullable=False, default=[])

    __mapper_args__ = {'polymorphic_on': type, 'polymorphic_identity': None}


class DbJobFile(Base):
    __tablename__ = 'job_files'

    id = Column(Integer, primary_key=True, nullable=False)
    job_id = Column(
        ForeignKey('jobs.id', ondelete='CASCADE'), index=True)
    file_id = Column(String(40), nullable=False, index=True)
    mimetype = Column(String(40))
    headers = Column(JSONType, default=None)


class DbJob(Base):
    __tablename__ = 'jobs'

    id = Column(Integer, primary_key=True, nullable=False)
    type = Column(String(40), nullable=False, index=True)
    user_id = Column(Integer, index=True)
    username = Column(String, index=True)
    session_id = Column(Integer, nullable=True, index=True)

    state = relationship(DbJobState, backref='job', uselist=False)
    result = relationship(
        DbJobResult, backref='job', uselist=False,
        foreign_keys=DbJobResult.id)
    files = relationship(DbJobFile, backref='job')

    __mapper_args__ = {'polymorphic_on': type}


WINDOWS = sys.platform.startswith('win')


# Message encryption
job_server_port = None
job_server_key = b''
job_server_iv = b''


def encrypt(msg):
    """
    Encrypt a job server communication message

    :param bytes msg: message to encrypt

    :return: encrypted message or original message if encryption is not enabled
    :rtype: bytes
    """
    if not job_server_key:
        return msg
    return AES.new(job_server_key, AES.MODE_CFB, job_server_iv).encrypt(msg)


def decrypt(msg):
    """
    Decrypt a job server communication message

    :param bytes msg: message to decrypt

    :return: decrypted message or original message if encryption is not enabled
    :rtype: bytes
    """
    if not job_server_key:
        return msg
    return AES.new(job_server_key, AES.MODE_CFB, job_server_iv).decrypt(msg)


class JobWorkerProcess(Process):
    """
    Job worker process class
    """
    abort_event = None

    def __init__(self, job_queue, result_queue):
        if WINDOWS:
            self.abort_event = Event()

        super(JobWorkerProcess, self).__init__(
            target=self.body, args=(job_queue, result_queue, self.abort_event))
        self.daemon = True

        self.start()

    def body(self, job_queue, result_queue, abort_event):
        """
        Job worker process

        :param multiprocessing.Queue job_queue: single-producer
            multiple-consumer task queue; holds incoming jobs -- serialized Job
            objects
        :param multiprocessing.Queue result_queue: multiple-producer
            single-consumer result queue; holds job state/result updates
        :param multiprocessing.Event abort_event: event object used to cancel
            a job; only used on Windows, other systems use OS signals

        :return: None
        """
        prefix = '[Job worker {}]'.format(os.getpid())

        if WINDOWS:
            # Start an extra thread waiting for abort event and raising
            # KeyboardInterrupt in the main thread context
            stop_event = Event()
            main_tid = threading.current_thread().ident

            def abort_event_listener_body():
                while True:
                    abort_event.wait()
                    if stop_event.is_set():
                        break
                    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
                        ctypes.c_long(main_tid),
                        ctypes.py_object(KeyboardInterrupt))
                    if res != 1:
                        ctypes.pythonapi.PyThreadState_SetAsyncExc(
                            ctypes.c_long(main_tid), None)

            abort_event_listener = threading.Thread(
                target=abort_event_listener_body)
            abort_event_listener.start()
        else:
            stop_event = abort_event_listener = None

        # Close all possible data file db engine connections inherited from the
        # parent process
        from . import data_files
        data_files.data_files_engine_lock = threading.Lock()
        for engine in data_files.data_files_engine.values():
            engine.dispose()

        # Wait for an incoming job request
        app.logger.info('%s Waiting for jobs', prefix)
        while True:
            # noinspection PyBroadException
            try:
                job_descr = job_queue.get()
                if not job_descr:
                    # Empty job request = terminate worker
                    app.logger.info('%s Terminating', prefix)
                    break
                app.logger.debug('%s Got job request: %s', prefix, job_descr)

                # Create job object from description; job_descr is guaranteed to
                # contain at least type, ID, and user ID, and the corresponding
                # job plugin is guaranteed to exist
                try:
                    job = job_types[job_descr['type']].__class__(
                        result_queue, **job_descr)
                except Exception as e:
                    # Report job creation error to job server
                    app.logger.warn(
                        '%s Could not create job', prefix, exc_info=True)
                    result_queue.put(dict(
                        id=job_descr['id'],
                        state=dict(progress=100, status='completed'),
                        result=dict(errors=[str(e)]),
                    ))
                    continue

                # Replace auth.current_user with a fake user db object
                # with the current user id and username for those modules
                # that need them; within a worker process, auth.current_user
                # is an AnonymousUser object with settable "id" and "username"
                # attrs
                if not hasattr(auth.current_user, 'id'):
                    from ..users import AnonymousUser
                    auth.current_user = AnonymousUser()
                auth.current_user.id = job.user_id
                auth.current_user.username = job.username

                # Clear the possible cancel request
                if WINDOWS:
                    abort_event.clear()

                # Notify the job server that the job is running and run it
                result_queue.put(dict(id=job_descr['id'], pid=self.ident))
                job.update()
                try:
                    if app.config.get('PROFILE'):
                        # Profile the job if enabled
                        print('{}\nProfiling job "{}" (ID {})'.format(
                            '-'*80, job.name, job.id))
                        cProfile.runctx(
                            'job.run()', {}, {'job': job}, sort='time')
                        print('-'*80)
                    else:
                        job.run()
                except KeyboardInterrupt:
                    # Job canceled
                    job.state.status = 'canceled'
                except Exception as e:
                    # Unexpected job exception
                    job.result.errors.append(str(e))
                finally:
                    # Notify the job server about job completion
                    if job.state.status != 'canceled':
                        job.state.status = 'completed'
                        job.state.progress = 100
                    job.state.completed_on = datetime.utcnow()
                    job.update()
                    result_queue.put(dict(id=None, pid=self.ident))

                    # Close the possible data file db session
                    # noinspection PyBroadException
                    try:
                        with data_files.data_files_engine_lock:
                            data_files.data_files_engine[
                                data_files.get_root(job.user_id)
                            ].remove()
                    except Exception:
                        pass

            except KeyboardInterrupt:
                # Ignore interrupt signals occasionally sent before the job has
                # started
                pass
            except Exception:
                app.logger.warn(
                    '%s Internal job queue error', prefix, exc_info=True)

        if WINDOWS:
            # Terminate abort event listener
            stop_event.set()
            abort_event.set()
            abort_event_listener.join()


class JobWorkerProcessWrapper(object):
    """
    Wrapper class that holds a :class:`JobWorkerProcess` instance and a job ID
    currently run by this process
    """
    process = None
    _job_id_lock = None
    _job_id = None

    @property
    def job_id(self):
        """Currently running job ID"""
        with self._job_id_lock.acquire_read():
            return self._job_id

    @job_id.setter
    def job_id(self, value):
        with self._job_id_lock.acquire_write():
            self._job_id = value

    @property
    def ident(self):
        """Worker process ID"""
        return self.process.ident

    def __init__(self, job_queue, result_queue):
        self._job_id_lock = RWLock()
        self.process = JobWorkerProcess(job_queue, result_queue)

    def cancel_current_job(self):
        """
        Send abort signal to the current job that is being executed by the
        worker process

        :return: None
        """
        if WINDOWS:
            self.process.abort_event.set()
        else:
            s = signal.SIGINT
            try:
                # In Python 3, SIGINT is a Signals enum instance
                s = s.value
            except AttributeError:
                pass
            # noinspection PyTypeChecker
            os.kill(self.ident, s)


db_field_type_mapping = {
    fields.Boolean: Boolean,
    fields.Date: Date,
    fields.DateTime: DateTime,
    fields.Decimal: Float,
    fields.Dict: JSONType,
    fields.Email: Text,
    fields.Float: Float,
    fields.Integer: Integer,
    fields.List: JSONType,
    fields.Nested: JSONType,
    fields.String: Text,
    fields.Time: Time,
    fields.TimeDelta: Integer,
    fields.UUID: Text,
    fields.Url: Text,
}

try:
    # noinspection PyUnresolvedReferences
    db_field_type_mapping[fields.LocalDateTime] = Text
except AttributeError:
    # Newer marshmallow does not have LocalDateTime
    pass


def subclass_from_schema(base_class, schema, plugin_name=None):
    """
    Create a subclass of DbJob or DbJobResult for the given job plugin

    :param base_class: base db model class
    :param schema: job plugin class instance
    :param str plugin_name: job plugin name; required for job result classes

    :return: new db model class
    """
    if schema.__class__ is JobResult:
        # Plugin does not define its own result schema; use job_results table
        return base_class

    if isinstance(schema, Job):
        kind = 'jobs'
    else:
        kind = 'job_results'

    if plugin_name is None:
        plugin_name = schema.type

    # Get job-specific fields that are missing from the base schema and map them
    # to SQLAlchemy column types; skip fields that have no db counterpart
    base_fields = sum(
        [list(c().fields.keys()) for c in schema.__class__.__bases__
         if issubclass(c, Schema)], [])
    new_fields = [(name, Column(db_field_type_mapping[type(field)],
                                default=field.default
                                if field.default != missing else None))
                  for name, field in schema.fields.items()
                  if name not in base_fields and
                  type(field) in db_field_type_mapping]
    if not new_fields:
        # No extra fields with respect to parent schema; use parent table
        return base_class

    # Create a subclass with __tablename__ and polymorphic_identity derived from
    # the job type ID
    return type(
        'Db' + schema.__class__.__name__,
        (base_class,),
        dict(
            [
                ('__tablename__', plugin_name + '_' + kind),
                ('id', Column(ForeignKey(base_class.__tablename__ + '.id',
                                         ondelete='CASCADE'),
                              primary_key=True, nullable=False)),
                ('__mapper_args__', {'polymorphic_identity': plugin_name}),
            ] + new_fields),
    )


msg_hdr = '!i'
msg_hdr_size = struct.calcsize(msg_hdr)


class JobRequestHandler(BaseRequestHandler):
    """
    Job TCP server request handler class
    """

    # noinspection PyUnresolvedReferences
    def handle(self):
        server = self.server
        # noinspection PyUnresolvedReferences
        session = self.server.session_factory()

        http_status = 200
        binary_result = False
        mimetype = None
        headers = None

        try:
            msg_len = self.request.recv(msg_hdr_size)
            if len(msg_len) < msg_hdr_size:
                raise JobServerError(reason='Missing message size')
            msg_len = struct.unpack(msg_hdr, msg_len)[0]

            nbytes = msg_len
            msg = b''
            while nbytes:
                s = self.request.recv(nbytes)
                if not s:
                    raise JobServerError(reason='Incomplete message')
                msg += s
                nbytes -= len(s)

            try:
                msg = json.loads(decrypt(msg))
                if not isinstance(msg, dict):
                    raise Exception()
            except Exception:
                raise JobServerError(reason='JSON dict expected')

            try:
                method = msg.pop('method').lower()
            except Exception:
                raise JobServerError(reason='Missing request method')

            if method == 'terminate':
                # Server shutdown request
                self.server.shutdown()
                self.server.server_close()
                return

            try:
                resource = msg.pop('resource').lower()
            except Exception:
                raise JobServerError(reason='Missing resource ID')

            try:
                user_id = msg['user_id']
            except Exception:
                raise JobServerError(reason='Missing user ID')

            if resource == 'jobs':
                if method == 'get':
                    job_id = msg.get('id')
                    if job_id is None:
                        # Return all user's jobs for the given client session;
                        # hide user id/name and result
                        result = []
                        for job in session.query(DbJob).filter(
                                DbJob.user_id == user_id,
                                DbJob.session_id == msg.get('session_id')):
                            res = job_types[job.type].__class__(
                                exclude=['user_id', 'username', 'result']
                            ).dump(job)
                            if marshmallow_version < (3, 0):
                                res = res[0]
                            result.append(res)
                    else:
                        # Return the given job
                        job = session.query(DbJob).get(job_id)
                        if job is None or job.user_id != user_id:
                            raise UnknownJobError(id=job_id)
                        result = job_types[job.type].__class__(
                            exclude=['user_id', 'result']).dump(job)
                        if marshmallow_version < (3, 0):
                            result = result[0]

                elif method == 'post':
                    # Submit a job
                    try:
                        job_type = msg['type']
                    except KeyError:
                        raise MissingFieldError(field='type')
                    if job_type not in server.db_job_types:
                        raise UnknownJobTypeError(type=msg['type'])

                    session_id = msg.get('session_id')
                    if session_id is not None and get_data_file_db(user_id).\
                            query(SqlaSession).get(session_id) is None:
                        raise ValidationError(
                            'session_id',
                            'Unknown session "{}"'.format(session_id), 404)

                    # Need an extra worker?
                    with server.pool_lock.acquire_read():
                        pool_size = len(server.pool)
                        busy_workers = len(
                            [p for p in server.pool if p.job_id is not None])
                    if busy_workers == pool_size:
                        # All workers are currently busy
                        if server.max_pool_size and \
                                pool_size >= server.max_pool_size:
                            app.logger.warn(
                                'All job worker processes are busy; '
                                'consider increasing JOB_POOL_MAX')
                        else:
                            app.logger.info(
                                'Adding one more worker to job pool')
                            with server.pool_lock.acquire_write():
                                server.pool.append(JobWorkerProcessWrapper(
                                    server.job_queue, server.result_queue))

                    try:
                        job = server.db_job_types[job_type](
                            state=DbJobState(),
                            result=server.db_job_result_types[job_type]()
                        )
                        for name, val in msg.items():
                            # noinspection PyBroadException
                            try:
                                # JSONType fields are not automatically
                                # converted on assignment; deserialize if a JSON
                                # string was passed in request arguments instead
                                # of a value (e.g. list)
                                if isinstance(
                                        getattr(job.__class__, name).property.
                                        columns[0].type, JSONType):
                                    val = json.loads(val)
                            except Exception:
                                pass
                            setattr(job, name, val)
                        session.add(job)
                        session.flush()
                        result = job_types[job_type].dump(job)
                        if marshmallow_version < (3, 0):
                            result = result[0]
                        server.job_queue.put(result)
                        result = dict(result)
                        del result['user_id'], result['username']
                        session.commit()
                    except Exception:
                        session.rollback()
                        raise

                    http_status = 201

                elif method == 'delete':
                    # Delete existing job
                    try:
                        job_id = msg['id']
                    except KeyError:
                        raise MissingFieldError(field='id')

                    job = session.query(DbJob).get(job_id)
                    if job is None or job.user_id != user_id:
                        raise UnknownJobError(id=job_id)

                    if job.state.status not in ('completed', 'canceled'):
                        raise CannotDeleteJobError(status=job.state.status)

                    # Delete job files
                    for jf in job.files:
                        try:
                            os.unlink(
                                job_file_path(user_id, job_id, jf.file_id))
                        except OSError:
                            pass

                    try:
                        session.query(DbJob).filter(DbJob.id == job_id).delete()
                        session.commit()
                    except Exception:
                        session.rollback()
                        raise

                    result = ''
                    http_status = 204

                else:
                    raise InvalidMethodError(
                        resource=resource, method=method.upper())

            elif resource == 'jobs/state':
                # Get/update job state
                try:
                    job_id = msg['id']
                except KeyError:
                    raise MissingFieldError(field='id')

                job = session.query(DbJob).get(job_id)
                if job is None or job.user_id != user_id:
                    raise UnknownJobError(id=job_id)

                if method == 'get':
                    # Return job state
                    result = JobState().dump(job.state)
                    if marshmallow_version < (3, 0):
                        result = result[0]

                elif method == 'put':
                    # Cancel job
                    try:
                        if msg['status'] != 'canceled':
                            raise CannotSetJobStatusError(status=msg['status'])
                    except KeyError:
                        raise MissingFieldError(field='status')

                    # Find worker process that is currently running the job
                    if job.state.status != 'in_progress':
                        raise CannotCancelJobError(status=job.state.status)

                    # Send abort signal to worker process running the given job.
                    # If no such process found, this means that the job either
                    # has not been dispatched yet or has been already completed;
                    # do nothing in both cases.
                    with server.pool_lock.acquire_read():
                        for p in server.pool:
                            if p.job_id == job_id:
                                p.cancel_current_job()
                                break

                    # Return the current job state
                    result = JobState().dump(job.state)
                    if marshmallow_version < (3, 0):
                        result = result[0]

                else:
                    raise InvalidMethodError(
                        resource=resource, method=method.upper())

            elif resource == 'jobs/result':
                if method == 'get':
                    # Return job result
                    try:
                        job_id = msg['id']
                    except KeyError:
                        raise MissingFieldError(field='id')

                    job = session.query(DbJob).get(job_id)
                    if job is None or job.user_id != user_id:
                        raise UnknownJobError(id=job_id)

                    result = job_types[job.type].fields['result'].schema.dump(
                        job.result)
                    if marshmallow_version < (3, 0):
                        result = result[0]

                else:
                    raise InvalidMethodError(
                        resource=resource, method=method.upper())

            elif resource == 'jobs/result/files':
                if method == 'get':
                    # Return extra job result file data
                    try:
                        job_id = msg['id']
                    except KeyError:
                        raise MissingFieldError(field='id')

                    try:
                        file_id = msg['file_id']
                    except KeyError:
                        raise MissingFieldError(field='file_id')

                    job_file = session.query(DbJobFile).filter_by(
                        job_id=job_id, file_id=file_id).one_or_none()
                    if job_file is None or job_file.job.user_id != user_id:
                        raise UnknownJobFileError(id=file_id)

                    try:
                        with open(job_file_path(user_id, job_id, file_id),
                                  'rb') as f:
                            result = f.read()
                    except Exception:
                        raise UnknownJobFileError(id=file_id)

                    binary_result = True
                    mimetype = job_file.mimetype
                    headers = job_file.headers

                else:
                    raise InvalidMethodError(
                        resource=resource, method=method.upper())

            else:
                raise JobServerError(
                    reason='Invalid resource "{}"'.format(resource))

        except AfterglowError as e:
            # Construct JSON error response in the same way as
            # errors.afterglow_error_handler()
            result = {
                'exception': e.__class__.__name__,
                'message': e.message if hasattr(e, 'message') and e.message
                else ', '.join(str(arg) for arg in e.args) if e.args
                else str(e),
            }
            if hasattr(e, 'payload') and e.payload:
                result.update(e.payload)
            if hasattr(e, 'subcode') and e.subcode:
                result['subcode'] = int(e.subcode)
            if getattr(e, 'code', 400) == 500:
                result['traceback'] = traceback.format_tb(sys.exc_info()[-1])
            http_status = int(e.code) if hasattr(e, 'code') and e.code else 400

        except Exception as e:
            # Wrap other exceptions in JobServerError
            # noinspection PyUnresolvedReferences
            result = {
                'exception': JobServerError.__name__,
                'message': JobServerError.message,
                'reason': e.message if hasattr(e, 'message') and e.message
                else ', '.join(str(arg) for arg in e.args) if e.args
                else str(e),
                'subcode': JobServerError.subcode,
                'traceback': traceback.format_tb(sys.exc_info()[-1]),
            }
            http_status = JobServerError.code

        # noinspection PyBroadException
        try:
            session.remove()
        except Exception:
            pass

        # Format response message, encrypt and send back to Flask
        msg = {}
        if binary_result:
            # Data (e.g. job file) to be sent in the HTTP response
            msg['body'] = result
            if mimetype:
                msg['mimetype'] = mimetype
        else:
            # JSON message
            msg['json'] = result
        if headers:
            msg['headers'] = headers
        msg['status'] = http_status

        # noinspection PyBroadException
        try:
            msg = encrypt(json.dumps(msg).encode('utf8'))
            self.request.sendall(struct.pack(msg_hdr, len(msg)) + msg)
        except Exception:
            # noinspection PyBroadException
            try:
                app.logger.warn(
                    'Error sending job server response', exc_info=True)
            except Exception:
                pass


def job_server(notify_queue, key, iv):
    """
    Main job server process

    :param multiprocessing.Queue notify_queue: queue used to send messages to
        the main process on the job server process initialization and errors
    :param bytes key: message encryption key
    :param bytes iv: message encryption initialization vector

    :return: None
    """
    global job_server_key, job_server_iv

    # Create sync structures
    job_queue = Queue()
    result_queue = Queue()
    terminate_listener_event = threading.Event()
    state_update_listener = None

    try:
        app.logger.info('Starting Afterglow job server (pid %d)', os.getpid())

        # Inherit encryption key/IV from the parent process
        job_server_key, job_server_iv = key, iv

        # Initialize job database
        # Create DbJob and DbJobResult subclasses for each job type based on
        # schema fields
        db_job_types, db_job_result_types = {}, {}
        for job_type, job_schema in job_types.items():
            db_job_types[job_type] = subclass_from_schema(
                DbJob, job_schema)
            db_job_result_types[job_type] = subclass_from_schema(
                DbJobResult, job_schema.fields['result'].nested(),
                job_schema.name)

        # Enable foreign keys in sqlite; required for ON DELETE CASCADE to work
        # when deleting jobs; set journal mode to WAL to allow concurrent access
        # from multiple Apache processes
        @event.listens_for(Engine, 'connect')
        def set_sqlite_pragma(dbapi_connection, _):
            if isinstance(dbapi_connection, sqlite3.Connection):
                cursor = dbapi_connection.cursor()
                cursor.execute('PRAGMA foreign_keys=ON')
                cursor.execute('PRAGMA journal_mode=WAL')
                cursor.close()

        # Recreate the job db on startup; also erase shared memory and journal
        # files
        db_path = os.path.join(
            os.path.abspath(app.config['DATA_ROOT']), 'jobs.db')
        for fp in glob(db_path + '*'):
            try:
                os.remove(fp)
            except OSError:
                pass
        engine = create_engine(
            'sqlite:///{}'.format(db_path),
            connect_args={'check_same_thread': False, 'isolation_level': None},
        )
        Base.metadata.create_all(bind=engine)
        session_factory = scoped_session(sessionmaker(bind=engine))

        # Erase old job files
        try:
            shutil.rmtree(job_file_dir)
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise

        # Initialize pool of worker processes
        min_pool_size = app.config.get('JOB_POOL_MIN', 1)
        max_pool_size = app.config.get('JOB_POOL_MAX', 16)
        if min_pool_size > 0:
            app.logger.info(
                'Starting %d job worker process%s', min_pool_size,
                '' if min_pool_size == 1 else 'es')
            pool = [JobWorkerProcessWrapper(job_queue, result_queue)
                    for _ in range(min_pool_size)]
        else:
            pool = []
        pool_lock = RWLock()

        # Listen for job state updates in a separate thread
        def state_update_listener_body():
            """
            Thread that listens for job state/result updates from worker
            processes and updates the corresponding database tables

            :return: None
            """
            while not terminate_listener_event.is_set():
                msg = result_queue.get()
                if not msg:
                    continue
                if not isinstance(msg, dict) or 'id' not in msg or \
                        'state' in msg and \
                        not isinstance(msg['state'], dict) or \
                        'result' in msg and not isinstance(msg['result'], dict):
                    app.logger.warn(
                        'Job state listener got unexpected message "%s"', msg)
                    continue

                job_id = msg['id']
                job_state = msg.get('state', {})
                job_result = msg.get('result', {})
                job_pid = msg.get('pid')
                job_file = msg.get('file')

                if job_pid is not None:
                    # Worker process assignment message
                    found = False
                    with pool_lock.acquire_read():
                        for p in pool:
                            if p.ident == job_pid:
                                p.job_id = job_id
                                found = True
                                break
                    if not found:
                        app.logger.warn(
                            'Job state listener got a job assignment message '
                            'for non-existent worker process %s', job_pid)
                    continue

                sess = session_factory()
                try:
                    if job_file is not None:
                        # Job file creation message
                        # noinspection PyBroadException
                        try:
                            sess.add(DbJobFile(
                                job_id=job_id,
                                file_id=job_file['id'],
                                mimetype=job_file.get('mimetype'),
                                headers=job_file.get('headers')))
                            sess.commit()
                        except Exception:
                            sess.rollback()
                            app.logger.warn(
                                'Could not add job file "%s" to database',
                                exc_info=True)
                        continue

                    if not job_state and not job_result:
                        # Empty message, nothing to do
                        continue

                    job = sess.query(DbJob).get(job_id)
                    if job is None:
                        # State update for a job that was already deleted;
                        # silently ignore
                        continue

                    # noinspection PyBroadException
                    try:
                        # Update job state
                        for name, val in job_state.items():
                            setattr(job.state, name, val)

                        # Update job result
                        for name, val in job_result.items():
                            setattr(job.result, name, val)

                        sess.commit()
                    except Exception:
                        sess.rollback()
                        app.logger.warn(
                            'Could not update job state/result "%s"',
                            msg, exc_info=True)
                finally:
                    sess.close()

        state_update_listener = threading.Thread(
            target=state_update_listener_body)
        state_update_listener.start()

        # Start TCP server, listen on any available port
        tcp_server = ThreadingTCPServer(('localhost', 0), JobRequestHandler)
        tcp_server.db_job_types = db_job_types
        tcp_server.db_job_result_types = db_job_result_types
        tcp_server.session_factory = session_factory
        tcp_server.job_queue = job_queue
        tcp_server.result_queue = result_queue
        tcp_server.pool = pool
        tcp_server.pool_lock = pool_lock
        tcp_server.min_pool_size = min_pool_size
        tcp_server.max_pool_size = max_pool_size

        # Send the actual port number to the main process
        notify_queue.put(('success', tcp_server.server_address[1]))
        app.logger.info('Afterglow job server started')

        # Serve job resource requests until requested to terminate
        tcp_server.serve_forever()

    except (KeyboardInterrupt, SystemExit):
        app.logger.info('Job server terminated')
    except Exception as e:
        # Make sure the main process receives at least an error message if job
        # server process initialization failed
        notify_queue.put(('exception', e))
        app.logger.warn('Error in job server process', exc_info=True)
    finally:
        # Shut down state update listener
        result_queue.put(None)
        terminate_listener_event.set()
        if state_update_listener is not None:
            state_update_listener.join()


@app.before_first_request
def init_jobs():
    """
    Initialize the job subsystem

    :return: None
    """
    global job_server_port, job_server_key, job_server_iv

    # Initialize message encryption
    if app.config.get('JOB_SERVER_ENCRYPTION', True):
        if Random is None or AES is None:
            app.logger.warn(
                'Job server encryption not enabled, please install '
                'pycryptodome or pycryptodomex')
        else:
            job_server_key = os.urandom(32)
            job_server_iv = Random.new().read(AES.block_size)

    # Start job server process
    notify_queue = Queue()
    p = Process(
        target=job_server, args=(notify_queue, job_server_key, job_server_iv))
    p.start()

    # Wait for initialization
    msg = notify_queue.get()
    if msg[0] == 'exception':
        # Job server initialization error
        raise msg[1]
    if msg[0] == 'success':
        job_server_port = msg[1]
    else:
        raise JobServerError(
            reason='Invalid job server initialization message "{}"'.format(msg))


def job_server_request(resource, **args):
    """
    Make a request to job server and return response

    :param str resource: resource ID: "jobs", "jobs/state", "jobs/result",
        "jobs/result/files"
    :param args: extra request arguments

    :return: Flask response object
    :rtype: flask.Response
    """
    try:
        # Prepare server message
        msg = request.args.to_dict()
        if args:
            msg.update(args)
        msg.update(dict(
            resource=resource,
            method=request.method,
            user_id=auth.current_user.id,
            username=auth.current_user.username,
        ))
        msg = encrypt(json.dumps(msg).encode('utf8'))

        # Send message
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('localhost', job_server_port))
        try:
            sock.sendall(struct.pack(msg_hdr, len(msg)) + msg)

            # Get response
            msg_len = sock.recv(msg_hdr_size)
            if len(msg_len) < msg_hdr_size:
                raise JobServerError(reason='Missing message size')
            msg_len = struct.unpack(msg_hdr, msg_len)[0]

            nbytes = msg_len
            msg = b''
            while nbytes:
                s = sock.recv(nbytes)
                if not s:
                    raise JobServerError(reason='Incomplete message')
                msg += s
                nbytes -= len(s)
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
        msg = json.loads(decrypt(msg))
        if not isinstance(msg, dict):
            raise Exception()
    except Exception:
        raise JobServerError(reason='JSON structure expected')

    # Parse job server response and create Flask response
    try:
        response = json_response(
            msg['json'], msg.get('status', 200 if msg['json'] else 204),
            headers=msg.get('headers'))
    except KeyError:
        try:
            response = Response(
                msg['body'],
                status=msg.get('status', 200 if msg['body'] else 204),
                headers=msg.get('headers'),
                mimetype=msg.get('mimetype', 'application/octet-stream'),
            )
        except KeyError:
            response = json_response()
    return response
