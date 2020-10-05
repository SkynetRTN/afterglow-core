"""
Afterglow Core: image sonification job schemas
"""

from marshmallow.fields import String, Integer, Nested

from .... import AfterglowSchema, Boolean, Float
from ..job import JobSchema


__all__ = ['SonificationJobSchema', 'SonificationSettingsSchema']


class SonificationSettingsSchema(AfterglowSchema):
    """Image sonification settings"""
    x: int = Integer(default=1)
    y: int = Integer(default=1)
    width: int = Integer(default=0)
    height: int = Integer(default=0)
    coord: str = String(default='rect')
    barycenter: bool = Boolean(default=False)
    tempo: float = Float(default=100)
    sampling_rate: int = Integer(default=44100)
    start_tone: int = Integer(default=0)
    num_tones: int = Integer(default=22)
    volume: int = Integer(default=16384)
    noise_volume: int = Integer(default=1000)
    bkg_scale: float = Float(default=1/64)
    threshold: float = Float(default=1.5)
    min_connected: int = Integer(default=5)
    hi_clip: float = Float(default=99.9)
    noise_lo: float = Float(default=50)
    noise_hi: float = Float(default=99.9)
    index_sounds: bool = Boolean(default=False)


class SonificationJobSchema(JobSchema):
    type = 'sonification'

    file_id: int = Integer()
    settings: SonificationSettingsSchema = Nested(
        SonificationSettingsSchema, default={})
    format: str = String(default='wav')
