"""
Afterglow Core: job schemas
"""
import os
import sys
import traceback
from datetime import datetime

import errno
from marshmallow.fields import Integer, List, Nested, String

from ... import app
from ...errors import MethodNotImplementedError
from ...errors.job import CannotCreateJobFileError
from .. import AfterglowSchema, DateTime, Float, Resource

__all__ = ['Job', 'JobResult', 'JobState', 'job_file_dir', 'job_file_path']


class JobState(AfterglowSchema):
    """
    Job state structure

    Attributes::
        status: current job status; set to "pending" when the job is created,
            changes to "in_progress" when it is dispatched to a worker process,
            "completed" when it's finished (no matter success or error), and
            "canceled" if it's canceled by the client
        created_on: time of job creation (UTC "YYYY-MM-DD HH:MM:SS.SSSSSS")
        completed_on: time of completion or cancellation
        progress: current job progress, a number from 0 to 100
    """
    status = String(default='in_progress')  # type: str
    created_on = DateTime()  # type: datetime
    completed_on = DateTime()  # type: datetime
    progress = Float(default=0)  # type: float

    def __init__(self, *args, **kwargs):
        """
        Create job state structure

        :param args: see :class:`afterglow_core.AfterglowSchema`
        :param kwargs: --//--
        """
        super(JobState, self).__init__(*args, **kwargs)

        self.created_on = datetime.utcnow()


class JobResult(AfterglowSchema):
    """
    Base class for job results

    Attributes::
        errors: list of error messages
        warnings: list of warnings issued by :meth:`Job.run`

    The job plugin class usually subclasses :class:`JobResult` to define custom
    result fields in addition to the above:

    class MyJobResult(JobResult):
        value1: fields.Integer()
        value2: fields.Float()
    """
    errors = List(String())  # type: list
    warnings = List(String())  # type: list

    def __init__(self, *args, **kwargs):
        super(JobResult, self).__init__(*args, **kwargs)

        self.errors = []
        self.warnings = []


class Job(Resource):
    """
    Base class for JSON-serializable job plugins

    Plugin modules are placed in the :mod:`afterglow_core.resources.job_plugins`
    subpackage and must subclass from a schema defined in
    :mod:`afterglow_core.models.jobs`, which, in turn, subclasses from
    :class:`Job`. A job plugin must define at least the job type name
    and implement :meth:`run`. Example:

    # placed in afterglow_core.models.jobs.my_job
    from . import Job
    class MyJobSchema(Job):
        # custom job schema fields
        ...

    # placed in afterglow_core.resources.job_plugins.my_job
    from ...models.jobs.my_job import MyJobSchema
    class MyJob(MyJobSchema):
        name = 'my_job'

        def run(self):
            ...

    Job parameters are defined by adding fields to the job schema and may have
    a flat structure (all fields are defined on the class level):

    class MyJobSchema(Job):
        ...
        param1 = fields.Integer(default=1)
        ...
    Alternatively, one may pack parameters in a separate class that should be
    a subclass of :class:`AfterglowSchema`:

    class MyJobSettings(AfterglowSchema):
        param1 = fields.Integer(default=1)
        ...

    class MyJobSchema(Job):
        ...
        settings = fields.Nested(MyJobSettings, default={})

    Job plugins may define job-specific result structures by subclassing from
    :class:`JobResult` and adding extra fields that store data to be returned
    to the caller by GET /jobs/[id]/result:

    # placed in afterglow_core.models.jobs.my_job
    from . import Job, JobResult
    class MyJobResult(JobResult):
        value = fields.Integer()

    class MyJobSchema(Job):
        ...
        result = fields.Nested(MyJobResult)

    :meth:`run` updates the result structure and notifies the job server in the
    following way:

        def run(self):
            ...
            self.result.value = ...
            self.update()
            ...

    Calling :meth:`update` is not necessary on the final result assignment; it
    is only needed for the possible intermediate result updates like those
    corresponding to the different steps of the algorithm or the individual
    files when processing multiple files:

    # --- afterglow_core.models.jobs.my_job ---
    class MyJobSettings(AfterglowSchema):
        file_ids = fields.List(fields.Integer, default=[])

    class MyJobResult(JobResult):
        values = fields.List(fields.Float, default=[])

    class MyJobSchema(Job):
        ...
        settings = fields.Nested(MyJobSettings, default={})
        result = fields.Nested(MyJobResult)

    # --- afterglow_core.resources.job_plugins.my_job ---
    class MyJob(MyJobSchema):
        def run(self):
            file_ids = self.settings.file_ids
            for file_no, file_id in enumerate(file_ids):
                try:
                    ...  # process file
                    self.result.values.append(...)
                except Exception as e:
                    self.add_error(
                        'Error processing file {}: {}'.format(file_id, e))
                    self.result.values.append(None)
                finally:
                    self.state.progress = (file_no + 1)/len(file_ids)*100
                    self.update()

    :meth:`run` may read and create the regular user data files by calling
    functions from :mod:`afterglow_core.resources.data_files` using
    self.user_id as the current user ID (works also for installations with no
    user authentication enabled):

    from ..data_files import (
        create_data_file, get_data_file, get_data_file_db, get_root)

    class MyJobResult(JobResult):
        file_id = fields.Integer()  # output data file ID

    class MyJobSchema(Job):
        ...
        file_id = fields.Integer()  # input data file ID

    class MyJob(MyJobSchema):
        def run(self):
            data, hdr = get_data_file(self.user_id, self.file_id)
            ...  # do some processing
            # create a new data file and return its ID
            adb = get_data_file_db(self.user_id)
            self.result.file_id = create_data_file(
                adb, None, get_root(self.user_id), data, hdr,
                duplicates='append', session_id=self.session_id,
            ).id

    In addition to the regular data files, a job may create extra "job files"
    containing any data that does not fit in the database and should be
    transferred to the client via GET /jobs/[id]/result/files/[file_id] as
    a file with specific content type. An example is WAV files produced by
    the sonification job. Within the job, multiple extra files are distinguished
    by their IDs assigned by :meth:`run`. See :meth:`create_job_file` for more
    info.

    When a job is canceled by the client via
    PUT /jobs/[id]/state?status=canceled, a KeyboardInterrupt is raised in
    :meth:`run`. No special action is needed to handle this unless the job needs
    to do some cleanup on cancellation; then :meth:`run` should catch
    KeyboardInterrupt and reraise it after all necessary cleanup measures are
    taken:

        def run(self):
            try:
                ...
            except KeyboardInterrupt:
                ... # do the cleanup
                raise

    Fields:
        id: unique integer job ID assigned automatically on job creation
        type: job type name; used when submitting a job via
            POST /jobs?type=`name`
        user_id: ID of the user who submitted the job
        session_id: ID of the client session (None = default anonymous session);
            new data files will be created with this session ID
        state: current job state, an instance of DbJobState
        result: job result structure, an instance of DbJobResult or its subclass

    Methods:
        run(): run the job
        update(): called by :meth:`run` after an intermediate job result change
        add_error(): called by run() to add an intermediate error message
        add_warning(): called by run() to add an warning message
        update_progress(): update the current job progress value (0 to 100)
        create_job_file(): save data to an extra job data file and register the
            file in the job database
    """
    __get_view__ = 'jobs'

    id = Integer(default=None)  # type: int
    type = String()  # type: str
    user_id = Integer(default=None)  # type: int
    session_id = Integer(default=None)  # type: int
    state = Nested(JobState)  # type: JobState
    result = Nested(JobResult)  # type: JobResult

    _queue = None

    name = None

    def __init__(self, queue=None, **kwargs):
        """
        Create a :class:`Job` instance; used both when loading job plugins and
        when creating a new job

        :param multiprocessing.Queue queue: job state/result queue used to pass
            job state updates to job server; unused when loading job plugins
        :param kwargs: job-specific parameters passed on job creation
        """
        super(Job, self).__init__(**kwargs)

        self._queue = queue
        self.type = self.name

        # Initialize to default state and result
        # noinspection PyTypeChecker
        self.state = {}
        # noinspection PyTypeChecker
        self.result = {}

    def run(self):
        """
        Run the job; fully implemented by job plugin

        :return: None
        """
        raise MethodNotImplementedError(
            class_name=self.__class__.__name__, method_name='run')

    def update(self):
        """
        Notify the job server about job state change; should be called after
        modifying any of the JobState or JobResult fields while the job is still
        in progress; also called automatically upon job completion

        :return: None
        """
        # Serialize and enqueue the job state and result along with the job ID
        self._queue.put(dict(
            id=self.id,
            state=self.state.dump(self.state),
            result=self.result.dump(self.result),
        ))

    def add_error(self, msg):
        """
        Add error message to Job.result.errors

        :param str msg: error message

        :return: None
        """
        if app.config.get('DEBUG'):
            msg = '{}\nTraceback (most recent call last):\n{}'.format(
                msg, traceback.format_tb(sys.exc_info()[-1]))
        self.result.errors.append(msg)
        self._queue.put(dict(
            id=self.id,
            result=dict(errors=self.result.errors),
        ))

    def add_warning(self, msg):
        """
        Add warning message to Job.result.warnings

        :param str msg: warning message

        :return: None
        """
        self.result.warnings.append(msg)
        self._queue.put(dict(
            id=self.id,
            result=dict(warnings=self.result.warnings),
        ))

    def update_progress(self, progress):
        """
        Update Job.state.progress

        :param float progress: job progress (0 to 100)

        :return: None
        """
        self.state.progress = progress
        self._queue.put(dict(
            id=self.id,
            state=dict(progress=progress),
        ))

    def create_job_file(self, id, data, mimetype=None, headers=None):
        """
        Create a new extra job file to be returned by
        GET /jobs/[id]/result/files

        :param id: extra job file ID; not necessarily integer but should be
            unique among other job files for this job type
        :param bytes data: file data
        :param str mimetype: optional MIME type of the file being created,
            returned in the Content-Type header by GET /jobs/[id]/result/files
        :param dict headers: optional extra headers to be returned by
            GET /jobs/[id]/result/files

        :return: None
        """
        # Write job file data to disk
        try:
            fp = job_file_path(self.user_id, self.id, id)
            try:
                os.makedirs(os.path.dirname(fp))
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise

            with open(fp, 'wb') as f:
                f.write(data)
        except Exception as e:
            raise CannotCreateJobFileError(id=id, reason=str(e))

        # Send message to add job file to db
        file_def = dict(id=id)
        if mimetype is not None:
            file_def['mimetype'] = mimetype
        if headers is not None:
            file_def['headers'] = headers
        self._queue.put(dict(id=self.id, file=file_def))


job_file_dir = os.path.join(
    os.path.abspath(app.config['DATA_ROOT']), 'job_files')


def job_file_path(user_id, job_id, file_id):
    """
    Return path to extra job file

    :param int | str user_id: user ID
    :param int | str job_id: job ID
    :param str file_id: job file ID

    :return: path to job file
    :rtype: str
    """
    if user_id:
        p = os.path.join(job_file_dir, str(user_id))
    else:
        p = job_file_dir
    return os.path.join(p, '{}_{}'.format(job_id, file_id))
