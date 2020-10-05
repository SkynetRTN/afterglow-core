"""
Afterglow Core: source extraction schemas
"""

from datetime import datetime

from marshmallow.fields import Integer, String

from ... import AfterglowSchema, DateTime, Float


__all__ = [
    'IAstrometrySchema', 'IFwhmSchema', 'ISourceIdSchema', 'ISourceMetaSchema',
    'SourceExtractionDataSchema',
]


class ISourceMetaSchema(AfterglowSchema):
    file_id = Integer()  # type: int
    time = DateTime()  # type: datetime
    filter = String()  # type: str
    telescope = String()  # type: str
    exp_length = Float()  # type: float


class IAstrometrySchema(AfterglowSchema):
    ra_hours = Float()  # type: float
    dec_degs = Float()  # type: float
    pm_sky = Float()  # type: float
    pm_pos_angle_sky = Float()  # type: float
    x = Float()  # type: float
    y = Float()  # type: float
    pm_pixel = Float()  # type: float
    pm_pos_angle_pixel = Float()  # type: float
    pm_epoch = DateTime()  # type: datetime
    flux = Float()  # type: float


class IFwhmSchema(AfterglowSchema):
    fwhm_x = Float()  # type: float
    fwhm_y = Float()  # type: float
    theta = Float()  # type: float


class ISourceIdSchema(AfterglowSchema):
    id = String()  # type: str


class SourceExtractionDataSchema(ISourceMetaSchema, IAstrometrySchema,
                                 IFwhmSchema, ISourceIdSchema):
    """
    Description of object returned by source extraction
    """
    pass
