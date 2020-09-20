"""
Afterglow Core: data provider schemas
"""

import json
from datetime import datetime

from marshmallow.fields import Dict, Integer, List, String

from ... import Boolean, DateTime, Resource


__all__ = ['DataFileSchema', 'SessionSchema']


class DataFileSchema(Resource):
    """
    JSON-serializable data file class

    Fields:
        id: unique integer data file ID; assigned automatically when creating
            or importing data file into session
        name: data file name; on import, set to the data provider asset name
        width: image width
        height: image height
        data_provider: for imported data files, name of the originating data
            provider; not defined for data files created from scratch or
            uploaded
        asset_path: for imported data files, the original asset path
        asset_metadata: dictionary of the originating data provider asset
            metadata
        layer: layer ID for data files imported from multi-layer data provider
            assets
        created_on: datetime.datetime of data file creation
        modified: True if the file was modified after creation
        modified_on: datetime.datetime of data file modification
    """
    __get_view__ = 'data_files'

    id = Integer(default=None)  # type: int
    type = String(default=None)  # type: str
    name = String(default=None)  # type: str
    width = Integer(default=None)  # type: int
    height = Integer(default=None)  # type: int
    data_provider = String(default=None)  # type: str
    asset_path = String(default=None)  # type: str
    asset_metadata = Dict(default={})  # type: dict
    layer = String(default=None)  # type: str
    created_on = DateTime(
        default=None, format='%Y-%m-%d %H:%M:%S')  # type: datetime
    modified = Boolean(default=False)
    modified_on = DateTime(
        default=None, format='%Y-%m-%d %H:%M:%S')  # type: datetime
    session_id = Integer(default=None)  # type: int

    def __init__(self, _obj=None, **kwargs):
        """
        Create a new data file schema

        :param :class:`SqlaDataFile` _obj: SQLA data file returned by database
            query
        :param kwargs: if `_obj` is not set, initialize the data file fields
            from the given keyword=value pairs
        """
        # Extract fields from SQLA object
        kw = {name: getattr(_obj, name, None)
              for name in self._declared_fields
              if name not in getattr(Resource, '_declared_fields')}
        kw.update(kwargs)

        # Convert fields stored as strings in the db to their proper schema
        # types
        if kw.get('asset_metadata') is not None:
            kw['asset_metadata'] = json.loads(kw['asset_metadata'])

        super(DataFileSchema, self).__init__(**kw)


class SessionSchema(Resource):
    """
    JSON-serializable Afterglow session class

    A session is a collection of user's data files. When creating or importing
    a data file, it is associated with a certain session (by default, if no
    session ID provided, with the anonymous session that always exists).
    Sessions are created by the user via the /sessions endpoint. Their main
    purpose is to provide independent Afterglow UI workspaces; in addition,
    they may serve as a means to group data files by the client API scripts.

    Fields:
        id: unique integer session ID; assigned automatically when creating
            the session
        name: unique session name
        data: arbitrary user data associated with the session
        data_file_ids: list of data file IDs associated with the session
    """
    __get_view__ = 'sessions'

    id = Integer(default=None)  # type: int
    name = String(default=None)  # type: str
    data = String()  # type: str
    data_file_ids = List(Integer(), default=[], dump_only=True)  # type: list

    def __init__(self, _obj=None, **kwargs):
        """
        Create a new session schema

        :param :class:`SqlaSession` _obj: SQLA session returned by database
            query
        :param kwargs: if `_obj` is not set, initialize the data file fields
            from the given keyword=value pairs
        """
        # Extract fields from SQLA object
        kw = {name: getattr(_obj, name, None)
              for name in self._declared_fields
              if name not in getattr(Resource, '_declared_fields')}
        kw.update(kwargs)

        # Extract data file IDs
        kw['data_file_ids'] = [data_file.id for data_file in _obj.data_files]

        super(SessionSchema, self).__init__(**kw)
