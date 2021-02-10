#!/usr/bin/env python

from afterglow_core import app


if __name__ == '__main__':
    app.run(threaded=False, use_reloader=False)
