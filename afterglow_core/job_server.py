"""
Afterglow Core: job server

Celery application that automatically converts Afterglow jobs into Celery tasks.
"""
import json
import os
import errno
import sys
import traceback
import ctypes
import signal
from datetime import datetime, timedelta
from threading import Event, Thread
from typing import Dict as TDict, Union
from types import SimpleNamespace
from urllib.parse import quote

from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, close_all_sessions, relationship
from alembic import config as alembic_config, context as alembic_context
from alembic.script import ScriptDirectory
from alembic.runtime.environment import EnvironmentContext
from werkzeug.http import HTTP_STATUS_CODES
from flask import Flask, current_app, g
from flask_login import current_user
from cryptography.fernet import Fernet

# Monkey-patch billiard.exceptions so that SoftTimeLimitExceeded subclasses BaseException and is not accidentally caught
# by jobs
import billiard.exceptions


class SoftTimeLimitExceeded(BaseException):
    """The soft time limit has been exceeded. This exception is raised
    to give the task a chance to clean up."""
    def __str__(self):
        return 'SoftTimeLimitExceeded%s' % (self.args,)


billiard.exceptions.SoftTimeLimitExceeded = SoftTimeLimitExceeded

from celery import Celery, Task, shared_task
from celery.exceptions import TaskRevokedError, WorkerLostError
from celery.result import AsyncResult
from celery.schedules import crontab
from celery.signals import after_setup_logger, after_setup_task_logger
from celery.loaders.app import AppLoader

from .database import db
from .resources.base import DateTime, JSONType
from .plugins import load_plugins
from .errors import AfterglowError, MissingFieldError
from .errors.job import *
from .resources import data_files
from .resources.users import DbUser
from .models import Job, job_file_path, job_result_dir, job_result_path


__all__ = ['init_jobs']


# Job state constants
js = SimpleNamespace()
js.PENDING = 'pending'
js.IN_PROGRESS = 'in_progress'
js.COMPLETED = 'completed'
js.CANCELED = 'canceled'

JOB_STATE_UPDATE_ATTEMPTS = 3


class DbJobState(db.Model):
    __tablename__ = 'job_states'

    id = Column(String(36), ForeignKey('jobs.id', ondelete='CASCADE'), index=True, primary_key=True)
    status = Column(String(16), nullable=False, index=True, default=js.PENDING)
    created_on = Column(DateTime, nullable=False)
    started_on = Column(DateTime, index=True)
    completed_on = Column(DateTime)
    progress = Column(Float, nullable=False, default=0, index=True)

    job: Mapped['DbJob'] = relationship()


class DbJob(db.Model):
    __tablename__ = 'jobs'

    id = Column(String(36), primary_key=True, nullable=False)
    type = Column(String(40), nullable=False, index=True)
    user_id = Column(Integer, index=True)
    session_id = Column(Integer, nullable=True, index=True)
    args = Column(JSONType)

    state: Mapped['DbJobState'] = relationship(back_populates='job')


# Register all job types
job_types = load_plugins('job', 'resources.job_plugins', Job)


class TaskAbortedError(BaseException):
    """
    Exception raised by SIGINT handler in the main worker thread context; a subclass of :class:`BaseException`, so that
    it is not accidentally caught by a job's exception handler
    """
    def __str__(self):
        return 'Job canceled by user'


job_cancel_ack_event = Event()
job_cancel_timeout: float


def cancel_watchdog() -> None:
    """
    Watchdog thread that kills the worker if job cancellation is not acknowledged in a timely manner
    """
    if not job_cancel_ack_event.wait(job_cancel_timeout):
        print('Killing worker')
        os.kill(os.getpid(), signal.SIGKILL)
    print('Terminated in a timely manner')


@shared_task(name='run_job', bind=True)
def run_job(task: Task, *args, **kwargs):
    """
    The one and only Celery task wrapping all Afterglow jobs

    :param task: Celery task instance
    :param args: extra positional arguments to Job()
    :param kwargs: job initialization parameters; must include at least "type" and other job-dependent parameters
    """
    pid = os.getpid()
    job_id = kwargs['id'] = task.request.id  # use task ID as job ID
    prefix = f'[Job worker {pid}@{task.request.hostname}]'
    current_app.logger.info('%s Got job request: %s', prefix, kwargs)

    # Create job object from description; kwargs is guaranteed to contain at least type, ID, and user ID, and
    # the corresponding job plugin is guaranteed to exist
    try:
        job = Job(*args, _task=task, **kwargs)
    except Exception:
        # Report job creation error to job server
        current_app.logger.warning('%s Could not create job', prefix, exc_info=True)
        raise

    user_id = getattr(job, 'user_id', None)

    # Run the job in a background thread; copy Flask app context from the main thread with a fake request context
    ctx = current_app.request_context({'wsgi.url_scheme': 'http', 'wsgi.errors': {}, 'REQUEST_METHOD': 'GET'})

    def job_thread_body():
        with ctx:
            try:
                # flask_login.current_user support
                if user_id is not None:
                    g._login_user = DbUser.query.get_or_404(user_id, 'Unknown user')

                for niter in range(JOB_STATE_UPDATE_ATTEMPTS):
                    # noinspection PyBroadException
                    try:
                        db_job = DbJob.query.get(job_id)
                        if db_job is None:
                            return
                        db_job.state.status = js.IN_PROGRESS
                        db_job.state.started_on = datetime.utcnow()
                        db.session.commit()
                    except Exception as e:
                        if niter < JOB_STATE_UPDATE_ATTEMPTS - 1:
                            current_app.logger.warning(
                                'Error updating job %s state to in_progress, retrying %s more time%s',
                                job_id, JOB_STATE_UPDATE_ATTEMPTS - niter - 1,
                                's' if JOB_STATE_UPDATE_ATTEMPTS - niter - 1 > 1 else '',
                                exc_info=True)

                        # noinspection PyBroadException
                        try:
                            db.session.rollback()
                        except Exception:
                            pass

                        if niter == JOB_STATE_UPDATE_ATTEMPTS - 1:
                            raise RuntimeError(f'Error updating job state to in_progress [{e}]')
                    else:
                        break

                job.run()

                # Upon successful completion, always set progress to 100%
                job.update_progress(100)
            except TaskAbortedError as e:
                # Notify watchdog thread as soon as possible that a cancellation exception was caught
                job_cancel_ack_event.set()

                job.state.status = js.CANCELED
                job.add_error(e)

            except Exception as e:
                # Unexpected job exception; Celery task still succeeds
                job.add_error(e)

            finally:
                # Avoid "Server has gone away" errors
                # noinspection PyBroadException
                try:
                    db.session.remove()
                except Exception:
                    pass

    job_thread = Thread(target=job_thread_body)
    job_thread.start()
    job_tid = job_thread.ident
    job_cancel_ack_event.clear()

    def abort_handler(*_args) -> None:
        # Upon receiving SIGINT, asynchronously raise TaskAbortedError in the job thread
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(job_tid), ctypes.py_object(TaskAbortedError))
        if res != 1:
            ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(job_tid), None)

        # Start watchdog thread that will kill the worker if abort request is not acknowledged in a timely fashion
        Thread(target=cancel_watchdog).start()

    default_abort_handler = signal.signal(signal.SIGINT, abort_handler)

    try:
        job_thread.join()
    finally:
        # Restore the normal SIGINT handling
        signal.signal(signal.SIGINT, default_abort_handler)

    # Save serialized result to job result file
    d = job_result_dir()
    try:
        os.makedirs(d)
    except OSError as _e_:
        if _e_.errno != errno.EEXIST:
            raise
    serialized = job.result.dumps(job.result)
    with open(os.path.join(d, job_id), 'wt', encoding='utf8') as f:
        print(serialized, file=f)

    current_app.logger.info('%s Job %s -> %s', prefix, job_id, serialized)


# noinspection PyBroadException
@shared_task(name='cleanup_jobs')
def cleanup_jobs() -> None:
    """
    Periodic task that erases jobs and job files older than 1 day
    """
    expiration = datetime.utcnow() - timedelta(days=1)
    count = 0
    try:
        for job_state in DbJobState.query.filter(DbJobState.created_on < expiration):
            job_id, user_id = job_state.id, job_state.job.user_id

            delete_job_data(user_id, job_id)
            DbJob.query.filter_by(id=job_id).delete()

            count += 1

        db.session.commit()

        if count:
            current_app.logger.info('Deleted %s expired job%s', count, 's' if count > 1 else '')

    except Exception:
        db.session.rollback()
        current_app.logger.warning('Error deleting expired jobs', exc_info=True)

    finally:
        # noinspection PyBroadException
        try:
            db.session.remove()
        except Exception:
            pass


celery_app: Celery


# Set up logging
# noinspection PyUnusedLocal
@after_setup_logger.connect
@after_setup_task_logger.connect
def setup_logger(logger, *args, **kwargs):
    from . import MaxLengthFormatter
    for handler in logger.handlers:
        handler.setFormatter(MaxLengthFormatter('%(asctime)s %(levelname)-8s %(message)s'))


def init_jobs(app: Flask, cipher: Fernet) -> Celery:
    """
    Initialize the job subsystem

    :param app: Flask app instance
    :param cipher: :class:`cryptography.fernet.Fernet` instance used for encryption throughout Afterglow Core
    """
    global celery_app, job_cancel_timeout

    job_cancel_timeout = app.config['JOB_CANCEL_TIMEOUT']

    # Recipe from https://flask.palletsprojects.com/en/2.2.x/patterns/celery/
    class AfterglowTask(Task):
        def __call__(self, *args, **kwargs) -> object:
            """Run the task inside a Flask app context"""
            with app.app_context():
                return self.run(*args, **kwargs)

        # def before_start(self, task_id: str, args: tuple, kwargs: dict) -> None:
        #     """Track the task start time"""
        #     with app.app_context():
        #         close_all_sessions()
        #
        #         for _ in range(3):
        #             try:
        #                 db_job = DbJob.query.get(task_id)
        #                 if db_job is None:
        #                     return
        #                 db_job.state.status = js.IN_PROGRESS
        #                 db_job.state.started_on = datetime.utcnow()
        #                 db.session.commit()
        #             except Exception:
        #                 current_app.logger.warning(
        #                     'Error updating job %s state to in_progress', task_id, exc_info=True)
        #                 try:
        #                     db.session.rollback()
        #                 except Exception:
        #                     pass
        #             else:
        #                 break

        # noinspection PyBroadException
        def after_return(self, status, retval, task_id, args, kwargs, einfo):
            """Persist the final task state in the database"""
            res = self.AsyncResult(task_id).result
            if isinstance(res, TaskRevokedError):
                # Save a more meaningful result if task was canceled
                status = 'ABORTED'
                self.update_state(state=status, meta={'result': retval})

            with app.app_context():
                try:
                    db_job = DbJob.query.get(task_id)
                    if db_job is None:
                        return
                    db_job.state.status = js.COMPLETED if status != 'ABORTED' else js.CANCELED
                    db_job.state.completed_on = datetime.utcnow()
                    try:
                        # Save the last progress if the task terminated prematurely or was aborted
                        db_job.state.progress = res['state']['progress']
                    except Exception:
                        pass
                    db.session.commit()
                except Exception:
                    try:
                        db.session.rollback()
                    except Exception:
                        pass

                close_all_sessions()

    class AfterglowAppLoader(AppLoader):
        """Custom Celery app loader"""
        def on_task_init(self, task_id: str, task: Task):
            """Called before a task is executed"""
            # Make sure that all connections are committed to the pool before the first db query
            close_all_sessions()

    # Create/upgrade job tables via Alembic
    cfg = alembic_config.Config()
    cfg.set_main_option(
        'script_location', os.path.abspath(os.path.join(__file__, '..', 'db_migration', 'jobs'))
    )
    script = ScriptDirectory.from_config(cfg)
    with EnvironmentContext(
            cfg, script, fn=lambda rev, _: script._upgrade_revs('head', rev), as_sql=False,
            starting_rev=None, destination_rev='head', tag=None), db.engine.connect() as connection:
        alembic_context.configure(connection=connection, version_table='alembic_version_jobs')

        with alembic_context.begin_transaction():
            alembic_context.run_migrations()

    # Decrypt RabbitMQ password
    broker_pass = app.config["JOB_SERVER_PASS"]
    if broker_pass:
        if not isinstance(broker_pass, bytes):
            broker_pass = broker_pass.encode('ascii')
        broker_pass = ':' + quote(cipher.decrypt(broker_pass).decode('utf8'))

    # Create Celery app
    celery_app = Celery('afterglow_core.job_server', task_cls=AfterglowTask, loader=AfterglowAppLoader)
    config = dict(
        broker_url=f'amqp://{quote(app.config["JOB_SERVER_USER"])}{broker_pass}@{app.config["JOB_SERVER_HOST"]}:'
                   f'{app.config["JOB_SERVER_PORT"]}/{app.config["JOB_SERVER_VHOST"]}',
        broker_connection_retry_on_startup=True,
        result_backend='db+' + app.config['SQLALCHEMY_DATABASE_URI'],
        database_engine_options=app.config['SQLALCHEMY_ENGINE_OPTIONS'],
        database_short_lived_sessions=True,
        task_default_queue='afterglow',
        task_track_started=True,
        task_soft_time_limit=app.config['JOB_TIMEOUT'],
        task_time_limit=app.config['JOB_TIMEOUT'] + app.config['JOB_CANCEL_TIMEOUT']
        if app.config['JOB_TIMEOUT'] else None,
        beat_schedule={
            'cleanup-jobs': dict(  # wipe expired jobs daily at 4am
                task='cleanup_jobs',
                schedule=crontab(hour='4', minute='0'),
            ),
        },
    )
    if sys.platform.startswith('win'):
        config.update(
            # https://stackoverflow.com/questions/41636273/celery-tasks-received-but-not-executing
            worker_pool='eventlet',
        )
    celery_app.config_from_object(config)
    # Workaround for Windows, https://stackoverflow.com/questions/75659790/flask-celery-attributeerrorcant-pickle-local-object-celery-init-app-locals
    # noinspection PyPropertyAccess
    celery_app.Task = AfterglowTask
    celery_app.set_default()
    app.extensions['celery'] = celery_app
    app.logger.info('Afterglow job server initialized')
    return celery_app


def get_job_state(db_job: DbJob) -> TDict[str, object]:
    """
    Return serialized job state for a given database job object; used by GET /jobs, GET /jobs/#, GET /jobs/#/state, and
    PUT /jobs/#/state

    :param db_job: database job object

    :return: serialized DbJobState
    """
    status = db_job.state.status
    result = {
        'status': status,
        'created_on': db_job.state.created_on,
        'started_on': db_job.state.started_on,
        'progress': db_job.state.progress,
        'completed_on': db_job.state.completed_on,
    }

    if status == js.PENDING:
        res = AsyncResult(db_job.id)
        if res.state == 'STARTED':
            # Task status updated in celery_taskmeta but not in job_states
            status = js.IN_PROGRESS
    else:
        res = None

    if status == js.IN_PROGRESS:
        # Extract progress info from broker
        if res is None:
            res = AsyncResult(db_job.id)
        if isinstance(res.result, (TaskRevokedError, WorkerLostError)):
            # This happens when the task did not respond to cancellation request and was killed or the worker process
            # was lost due to SIGSEGV, OOM, etc.
            result['status'] = js.CANCELED
        else:
            # noinspection PyBroadException
            try:
                result['progress'] = res.result['state']['progress']
            except Exception:
                pass
    elif status == js.COMPLETED:
        result['progress'] = 100

    return result


def get_job_result(db_job: DbJob) -> TDict[str, object]:
    """
    Return serialized job result for a given database job object; used by GET /jobs, GET /jobs/#, and GET /jobs/#/result

    :param db_job: database job object

    :return: serialized DbJobResult or subclass
    """
    res = AsyncResult(db_job.id)
    res_schema = job_types[db_job.type].fields['result'].nested
    if res.state == 'SUCCESS':
        with open(job_result_path(db_job.id), 'rt', encoding='utf8') as f:
            result = json.load(f)
        result = res_schema(**result).to_dict()
    else:
        result = res_schema().to_dict()
    result['type'] = db_job.type

    if res.state in ('REVOKED', 'FAILURE'):
        exc = res.result
        if isinstance(exc, TaskRevokedError):
            # Translate TaskRevokedError returned if the worker was killed on cancellation into
            # the same exception (TaskAbortedError) as returned on normal cancellation, although
            # without traceback
            exc = TaskAbortedError()
        result.setdefault('errors', []).append({
            'id': exc.__class__.__name__,
            'detail': str(exc) or exc.__class__.__name__,
            'meta': {'traceback': res.traceback} if res.traceback else {},
        })

    return result


# noinspection PyBroadException
def delete_job_data(user_id: Union[int, str], job_id: str) -> None:
    """
    Delete the given job data: job result file and the optional job files

    :param user_id: user ID
    :param job_id: job ID
    """
    # Get job result from file
    res_path = job_result_path(job_id)
    try:
        with open(res_path, 'rt', encoding='utf8') as f:
            res = json.load(f)

        # Delete job files
        try:
            for file_id in res['files']:
                try:
                    os.unlink(job_file_path(user_id, job_id, file_id))
                except Exception:
                    current_app.logger.warning(
                        'Error deleting file "%s" for expired job %s, user %s',
                        file_id, job_id, user_id, exc_info=True)
        except Exception:
            pass

        # Delete job result file
        os.unlink(res_path)
    except Exception:
        pass


def job_server_request(resource: str, method: str, **args) -> TDict[str, object]:
    """
    Make a request to job server and return response; must be called within a Flask request context

    :param resource: resource ID, either "jobs", "jobs/state", "jobs/result", or "jobs/result/files"
    :param method: request method: "get", "post", "put", or "delete"
    :param args: extra request-specific arguments

    :return: response message
    """
    user_id = getattr(current_user, 'id', None)
    resource = resource.lower()
    method = method.lower()

    http_status = 200

    job_id = args.get('id')
    try:
        if job_id is None:
            if resource != 'jobs':
                raise MissingFieldError(field='id')

            if method == 'post':
                # Submit a job
                try:
                    job_type = args['type']
                except KeyError:
                    raise MissingFieldError(field='type')
                if job_type not in job_types:
                    raise UnknownJobTypeError(type=job_type)

                # Check that the specified session exists
                session_id = args.get('session_id')
                if session_id is not None:
                    data_files.get_session(user_id, session_id)

                args['user_id'] = user_id

                created_on = datetime.utcnow()

                # Start a Celery task
                res: AsyncResult = run_job.delay(**args)
                job_id = res.id

                # Convert message arguments to polymorphic job model and store it in the database
                try:
                    result = Job(**args).to_dict()
                    result['id'] = job_id
                    result['state']['created_on'] = created_on
                    job_args = dict(result)
                    del job_args['state'], job_args['result']
                    # Delete the common indexable fields
                    for name in ('id', 'type', 'user_id', 'session_id'):
                        del job_args[name]
                    db.session.add(DbJob(
                        id=job_id,
                        type=job_type,
                        user_id=user_id,
                        session_id=session_id,
                        args=job_args,
                    ))
                    db.session.add(DbJobState(id=job_id, created_on=created_on))
                    db.session.commit()
                except Exception:
                    db.session.rollback()
                    raise

                http_status = 201

            elif method == 'get':
                # Return all user's jobs for the given client session
                session_id = args.get('session_id')
                if session_id is not None:
                    data_files.get_session(user_id, session_id)
                result = []
                try:
                    for db_job in DbJob.query.filter(DbJob.user_id == user_id, DbJob.session_id == session_id):
                        result.append(dict(
                            id=db_job.id,
                            type=db_job.type,
                            user_id=db_job.user_id,
                            session_id=db_job.session_id,
                            state=get_job_state(db_job),
                            result=get_job_result(db_job),
                        ))
                        result[-1].update(db_job.args)
                except Exception:
                    db.session.rollback()
                    raise

            else:
                # PUT/DELETE are only applicable when a job ID is present
                raise MissingFieldError(field='id')

        else:
            # Request for an individual job or its state/result
            # Since Celery provides no way to check for the existence of a task, we need to hit the db even to get state
            # or result, both of which are stored in Celery
            try:
                db_job = DbJob.query.get(job_id)
                if db_job is None or db_job.user_id != user_id:
                    raise UnknownJobError(id=job_id)

                if method == 'get':
                    # Return an individual job or its elements
                    match resource:
                        case 'jobs':
                            # Return only the common Job fields plus job-specific fields, without state and result
                            result = dict(
                                id=db_job.id,
                                type=db_job.type,
                                user_id=db_job.user_id,
                                session_id=db_job.session_id,
                                state=get_job_state(db_job),
                                result=get_job_result(db_job),
                            )
                            result.update(db_job.args)

                        case 'jobs/state':
                            result = get_job_state(db_job)

                        case 'jobs/result':
                            result = get_job_result(db_job)

                        case 'jobs/result/files':
                            try:
                                file_id = args['file_id']
                            except KeyError:
                                raise MissingFieldError(field='file_id')

                            result = get_job_result(db_job)
                            try:
                                job_file = result['files'][file_id]
                            except (KeyError, TypeError):
                                raise UnknownJobFileError(id=file_id)
                            result = {
                                'filename': job_file_path(user_id, job_id, file_id),
                                'mimetype': job_file.get('mimetype') or 'application/octet-stream',
                                'headers': job_file.get('headers'),
                            }

                        case _:
                            raise ValueError(f'Invalid resource ID: "{resource}"')

                elif method == 'put':
                    # Cancel running job
                    if resource != 'jobs/state':
                        raise ValueError(f'Invalid resource ID: "{resource}"')
                    try:
                        status = args['status']
                    except KeyError:
                        raise MissingFieldError(field='status')
                    if status != js.CANCELED:
                        raise CannotSetJobStatusError(status=status)
                    if db_job.state.status != js.IN_PROGRESS:
                        raise CannotCancelJobError(status=db_job.state.status)

                    AsyncResult(job_id).revoke(terminate=True, signal='INT')

                    result = get_job_state(db_job)

                elif method == 'delete':
                    if resource != 'jobs':
                        raise ValueError(f'Invalid resource ID: "{resource}"')
                    if db_job.state.status not in (js.COMPLETED, js.CANCELED):
                        raise CannotDeleteJobError(status=db_job.state.status)

                    delete_job_data(user_id, job_id)

                    DbJob.query.filter_by(id=job_id).delete()
                    db.session.commit()

                    result = ''
                    http_status = 204

                else:
                    raise InvalidMethodError(resource=resource, method=method)

            except Exception:
                db.session.rollback()
                raise

    except AfterglowError as e:
        # Construct JSON error response in the same way as errors.afterglow_error_handler()
        http_status = int(getattr(e, 'code', 0)) or 400
        result = {
            'status': HTTP_STATUS_CODES.get(http_status, '{} Unknown Error'.format(http_status)),
            'id': str(getattr(e, 'id', e.__class__.__name__)),
            'detail': str(e) or e.__class__.__name__,
        }
        meta = getattr(e, 'meta', None)
        if meta:
            result['meta'] = dict(meta)
        result.setdefault('meta', {})['traceback'] = traceback.format_tb(sys.exc_info()[-1]),

    except Exception as e:
        # Wrap other exceptions in JobServerError
        http_status = JobServerError.code
        result = {
            'status': HTTP_STATUS_CODES[http_status],
            'id': e.__class__.__name__,
            'detail': str(e) or e.__class__.__name__,
            'meta': {'traceback': traceback.format_tb(sys.exc_info()[-1])},
        }

    return {'json': result, 'status': http_status}
