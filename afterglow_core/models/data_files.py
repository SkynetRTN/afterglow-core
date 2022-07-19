"""
Afterglow Core: data file and session models
"""

from datetime import datetime
from typing import Any, Dict as TDict, List as TList, Optional

from marshmallow.fields import Dict, Integer, List, Nested, String

from ..schemas import AfterglowSchema, Boolean, DateTime


__all__ = ['DataFile', 'Session']


class DataFile(AfterglowSchema):
    """
    Data file model

    Fields:
        id: unique integer data file ID; assigned automatically when creating
            or importing data file into session
        type: "image" or "table"
        name: data file name; on import, set to the data provider asset name
        width: image width or number of table columns
        height: image height or number of table rows
        data_provider: for imported data files, name of the originating data
            provider; not defined for data files created from scratch or
            uploaded
        asset_path: for imported data files, the original asset path
        asset_type: original asset file type ("FITS", "JPEG", etc.)
        asset_metadata: dictionary of the originating data provider asset
            metadata
        layer: layer ID for data files imported from multi-layer data provider
            assets
        created_on: datetime.datetime of data file creation
        modified: True if the file was modified after creation
        modified_on: datetime.datetime of data file modification
        session_id: ID of session if the data file is associated with a session
        group_name: name of the data file group
        group_order: 0-based order of the data file in the group
    """
    id: int = Integer(dump_default=None)
    type: str = String(dump_default=None)
    name: str = String(dump_default=None)
    width: int = Integer(dump_default=None)
    height: int = Integer(dump_default=None)
    data_provider: str = String(dump_default=None)
    asset_path: str = String(dump_default=None)
    asset_type: str = String(dump_default=None)
    asset_metadata: TDict[str, Any] = Dict(dump_default={})
    layer: str = String(dump_default=None)
    created_on: datetime = DateTime(
        dump_default=None, format='%Y-%m-%d %H:%M:%S.%f')
    modified: bool = Boolean(dump_default=False)
    modified_on: datetime = DateTime(
        dump_default=None, format='%Y-%m-%d %H:%M:%S.%f')
    session_id: Optional[int] = Integer(dump_default=None)
    group_name: str = String(dump_default=None)
    group_order: int = Integer(dump_default=0)


class Session(AfterglowSchema):
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
        data_files: list of data file objects associated with the session
    """
    id: int = Integer(dump_default=None)
    name: str = String(dump_default=None)
    data: str = String()
    data_files: TList[DataFile] = List(
        Nested(DataFile), dump_default=[], dump_only=True)
