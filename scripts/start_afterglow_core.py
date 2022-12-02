#!/usr/bin/env python

if __name__ in ('__main__', 'start_afterglow_core'):
    # Running in dev environment
    from afterglow_core import create_app
    app = create_app()

    with app.app_context():
        from afterglow_core.job_server import init_jobs
        init_jobs()

    if __name__ == '__main__':
        app.run(threaded=False, use_reloader=False)
