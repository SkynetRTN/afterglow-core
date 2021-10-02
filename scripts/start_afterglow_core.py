#!/usr/bin/env python
from afterglow_core import app


if __name__ in ('__main__', 'start_afterglow_core'):
    # Running in dev environment
    from afterglow_core.job_server import init_jobs
    init_jobs()
    if __name__ == '__main__':
        app.run(threaded=False, use_reloader=False)
