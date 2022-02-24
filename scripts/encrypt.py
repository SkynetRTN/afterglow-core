#!/usr/bin/env python

"""
Encrypt console input

Must be run in the Afterglow data directory (DATA_ROOT)!
"""

from afterglow_core import cipher


if __name__ == '__main__':
    print(cipher.encrypt(input().encode('utf8')))
