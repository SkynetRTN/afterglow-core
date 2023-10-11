#!/usr/bin/env python

if __name__ in ('__main__', 'start_afterglow_core'):
    # Running in dev environment
    from afterglow_core import app
    app.run(threaded=False, use_reloader=False)
