"""
Afterglow Core: common job schema defs
"""

from datetime import datetime
from typing import Optional

from marshmallow.fields import Integer, List, Nested, String

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
        completed_on: time of completion or cancellation
        progress: current job progress, a number from 0 to 100
    """
    status = String(default='in_progress')  # type: str
    created_on = DateTime()  # type: datetime
    completed_on = DateTime()  # type: datetime
    progress = Float(default=0)  # type: float


class JobResultSchema(AfterglowSchema):
    """
    Base class for job result schemas

    Fields::
        errors: list of error messages
        warnings: list of warnings issued by :meth:`Job.run`
    """
    errors = List(String(), default=[])  # type: list
    warnings = List(String(), default=[])  # type: list


class JobSchema(Resource):
    """
    Base class for job schemas

    Fields::
        id: unique integer job ID assigned automatically on job creation
        type: job type name; used when submitting a job via
            POST /jobs?type=`name`
        user_id: ID of the user who submitted the job
        session_id: ID of the client session (None = default anonymous session);
            new data files will be created with this session ID
        state: current job state, an instance of JobState
        result: job result structure, an instance of JobResult or its subclass
    """
    __polymorphic_on__ = 'type'
    __get_view__ = 'jobs'

    id = Integer(default=None)  # type: int
    type = String()  # type: str
    user_id = Integer(default=None)  # type: int
    session_id = Integer(default=None)  # type: Optional[int]
    state = Nested(JobStateSchema, default={})  # type: JobStateSchema
    result = Nested(JobResultSchema, default={})  # type: JobResultSchema
