#!/usr/bin/env python

"""
Encrypt console input

Must be run in the Afterglow data directory (DATA_ROOT) or pass the directory
containing AFTERGLOW_CORE_KEY on the command line
"""

import os
import sys
from base64 import urlsafe_b64encode

from cryptography.fernet import Fernet


if __name__ == '__main__':
    try:
        path = sys.argv[1]
    except IndexError:
        path = '.'
    with open(os.path.join(path, 'AFTERGLOW_CORE_KEY'), 'rb') as f:
        key = f.read()
    cipher = Fernet(urlsafe_b64encode(key + b'Afterglo'))
    print(cipher.encrypt(input().encode('utf8')).decode('ascii'))
