"""
Afterglow Core: Afterglow-wide database access
"""

import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from cryptography.fernet import Fernet


__all__ = ['db', 'init_db']


db = SQLAlchemy()


def init_db(app: Flask, cipher: Fernet) -> None:
    """
    Initialize the job subsystem

    :param app: Flask app instance
    :param cipher: :class:`cryptography.fernet.Fernet` instance used for encryption throughout Afterglow Core
    """
    # Set up SQLAlchemy options
    _db_pass = app.config.get('DB_PASS', '')
    if _db_pass:
        if not isinstance(_db_pass, bytes):
            _db_pass = _db_pass.encode('ascii')
        _db_pass = cipher.decrypt(_db_pass).decode('utf8')
    app.config['SQLALCHEMY_DATABASE_URI'] = \
        f'{app.config["DB_BACKEND"]}://{app.config["DB_USER"]}{":" + _db_pass if _db_pass else ""}@' \
        f'{app.config["DB_HOST"]}:{app.config["DB_PORT"]}/{app.config["DB_SCHEMA"]}'
    app.config.setdefault('SQLALCHEMY_ENGINE_OPTIONS', {})['pool_timeout'] = app.config['DB_TIMEOUT']
    app.config['SQLALCHEMY_ENGINE_OPTIONS'].setdefault('pool_recycle', 3600)
    app.config['SQLALCHEMY_ENGINE_OPTIONS'].setdefault('pool_size', app.config['DB_POOL_SIZE'])
    app.config['SQLALCHEMY_ENGINE_OPTIONS'].setdefault('pool_pre_ping', False)
    app.config.setdefault('SQLALCHEMY_TRACK_MODIFICATIONS', False)

    db.init_app(app)
