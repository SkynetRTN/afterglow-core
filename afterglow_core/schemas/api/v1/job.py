"""
Afterglow Core: common job schema defs
"""

from datetime import datetime
from typing import Dict, List as TList, Optional, Union

from marshmallow.fields import Integer, List, Nested, String

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
        completed_on: time of completion or cancellation
        progress: current job progress, a number from 0 to 100
    """
    status: str = String(default='in_progress')
    created_on: datetime = DateTime()
    completed_on: datetime = DateTime()
    progress: float = Float(default=0)


class JobResultSchema(AfterglowSchema):
    """
    Base class for job result schemas

    Fields::
        errors: list of error messages
        warnings: list of warnings issued by :meth:`Job.run`
    """
    errors: TList[Dict[str, Union[str, int, float, bool]]] = List(
        Nested(AfterglowErrorSchema), default=[])
    warnings: TList[str] = List(String(), default=[])


class JobSchema(Resource):
    """
    Base class for job schemas

    Fields::
        id: unique integer job ID assigned automatically on job creation
        type: job type name; used when submitting a job via
            POST /jobs?type=`name`
        user_id: ID of the user who submitted the job
        session_id: ID of the client session (None = default anonymous
            session); new data files will be created with this session ID
        state: current job state, an instance of JobState
        result: job result structure, an instance of JobResult or its subclass
    """
    __polymorphic_on__ = 'type'
    __get_view__ = 'jobs'

    id: int = Integer(default=None)
    type: str = String()
    user_id: int = Integer(default=None)
    session_id: Optional[int] = Integer(default=None)
    state: JobStateSchema = Nested(JobStateSchema, default={})
    result: JobResultSchema = Nested(JobResultSchema, default={})
