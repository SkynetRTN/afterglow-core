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
    file_id: int = Integer()
    time: datetime = DateTime()
    filter: str = String()
    telescope: str = String()
    exp_length: float = Float()


class IAstrometrySchema(AfterglowSchema):
    ra_hours: float = Float()
    dec_degs: float = Float()
    pm_sky: float = Float()
    pm_pos_angle_sky: float = Float()
    x: float = Float()
    y: float = Float()
    pm_pixel: float = Float()
    pm_pos_angle_pixel: float = Float()
    pm_epoch: datetime = DateTime()
    flux: float = Float()
    sat_pixels: int = Integer()


class IFwhmSchema(AfterglowSchema):
    fwhm_x: float = Float()
    fwhm_y: float = Float()
    theta: float = Float()


class ISourceIdSchema(AfterglowSchema):
    id: str = String()


class SourceExtractionDataSchema(ISourceMetaSchema, IAstrometrySchema,
                                 IFwhmSchema, ISourceIdSchema):
    """
    Description of object returned by source extraction
    """
    pass
