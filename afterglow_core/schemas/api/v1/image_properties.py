"""
Afterglow Core: image property extraction data structures
"""

from typing import Optional

from marshmallow.fields import Integer

from ... import AfterglowSchema, Float


__all__ = ['ImagePropertiesSchema']


class ImagePropertiesSchema(AfterglowSchema):
    """
    Result of field calibration for a data file
    """
    """
    Result of extraction of image properties (seeing etc.)
    """
    file_id: int = Integer()
    background_counts: Optional[float] = Float()
    background_rms_counts: Optional[float] = Float()
    num_sources: Optional[int] = Integer()
    num_saturated_sources: Optional[int] = Integer()
    seeing_pixels: Optional[float] = Float()
    seeing_arcsec: Optional[float] = Float()
    ellipticity: Optional[float] = Float()
    global_snr: Optional[float] = Float()
    sharpness: Optional[float] = Float()
