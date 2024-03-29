"""
Afterglow Core: common job schema defs
"""

from datetime import datetime
from typing import Dict as TDict, List as TList, Optional, Union

from marshmallow.fields import Dict, Integer, List, Nested, String

from ....models.errors import AfterglowError as AfterglowErrorSchema
from ... import AfterglowSchema, DateTime, Float, Resource


__all__ = ['JobResultSchema', 'JobSchema', 'JobStateSchema']


class JobStateSchema(AfterglowSchema):
    """
    Job state structure

    Fields::
        status: current job status; set to "pending" when the job is created,
            changes to "in_progress" when it is dispatched to a worker process,
            "completed" when it's finished (no matter success or error), and
            "canceled" if it's canceled by the client
        created_on: time of job creation (UTC "YYYY-MM-DD HH:MM:SS.SSSSSS")
        started_on: time of actual job start
        completed_on: time of completion or cancellation
        progress: current job progress, a number from 0 to 100
    """
    status: str = String(dump_default='pending')
    created_on: datetime = DateTime()
    started_on: datetime = DateTime()
    completed_on: datetime = DateTime()
    progress: float = Float()


class JobFileSchema(AfterglowSchema):
    """
    Job file definition; a dictionary of such objects can be put in JobResult.files via :meth:`Job.create_job_file`

    Attributes::
        mimetype: optional MIME file type
        headers: optional HTTP headers
    """
    mimetype: Optional[str] = String()
    headers: Optional[TDict[str, str]] = Dict(String, String)


class JobResultSchema(AfterglowSchema):
    """
    Base class for job result schemas

    Fields::
        errors: list of error messages
        warnings: list of warnings issued by :meth:`Job.run`
        files: dictionary of optional job files generated by the job
    """
    errors: TList[TDict[str, Union[str, int, float, bool]]] = List(Nested(AfterglowErrorSchema), dump_default=[])
    warnings: TList[str] = List(String(), dump_default=[])
    files: TDict[str, JobFileSchema] = Dict(String, Nested(JobFileSchema), dump_default={})


class JobSchema(Resource):
    """
    Base class for job schemas

    Fields::
        id: unique UUID-like job ID assigned automatically on job creation
        type: job type name; used when submitting a job via
            POST /jobs?type=`name`
        user_id: ID of the user who submitted the job
        session_id: ID of the client session (None = default anonymous
            session); new data files will be created with this session ID
        state: current job state, an instance of JobState
        result: job result structure, an instance of JobResult or its subclass
    """
    __polymorphic_on__ = 'type'
    __get_view__ = 'jobs.jobs'

    id: str = String(dump_default=None)
    type: str = String()
    user_id: int = Integer(dump_default=None)
    session_id: Optional[int] = Integer(dump_default=None)
    state: JobStateSchema = Nested(JobStateSchema, dump_default={})
    result: JobResultSchema = Nested(JobResultSchema, dump_default={})
