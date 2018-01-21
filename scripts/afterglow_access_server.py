#!/usr/bin/env python
from __future__ import absolute_import, division, print_function

from afterglow_server import app


if __name__ == '__main__':
    app.run(threaded=False)
