"""
Afterglow Core: job plugin package

A job plugin must define a custom model subclassing from
:class:`afterglow_core.models.jobs.Job`, along with the optional custom result
and settings models (subclassing from
:class:`afterglow_core.models.jobs.JobResult` and
:class:`afterglow_core.schemas.AfterglowSchema`, respectively), and implement
:meth:`Job.run`.
"""
