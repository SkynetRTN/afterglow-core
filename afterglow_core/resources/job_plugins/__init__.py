"""
Afterglow Core: job plugin package

A job plugin must define a custom schema in :mod:`afterglow_core.models.jobs`
subclassing from :class:`afterglow_core.models.jobs.Job`, along with
the optional custom result and settings schemas (subclassing from
:class:`afterglow_core.models.jobs.JobResult` and
:class:`afterglow_core.models.AfterglowSchema`, respectively), and subclass it
in :mod:`afterglow_core.resources.job_plugins`, implementing :meth:`Job.run`.
"""
