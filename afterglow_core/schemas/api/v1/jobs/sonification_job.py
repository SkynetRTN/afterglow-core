"""
Afterglow Core: image sonification job schemas
"""

from marshmallow.fields import String, Integer, Nested

from .... import AfterglowSchema, Boolean, Float
from ..job import JobSchema


__all__ = ['SonificationJobSchema', 'SonificationSettingsSchema']


class SonificationSettingsSchema(AfterglowSchema):
    """Image sonification settings"""
    x: int = Integer(dump_default=1)
    y: int = Integer(dump_default=1)
    width: int = Integer(dump_default=0)
    height: int = Integer(dump_default=0)
    coord: str = String(dump_default='rect')
    barycenter: bool = Boolean(dump_default=False)
    tempo: float = Float(dump_default=100)
    sampling_rate: int = Integer(dump_default=44100)
    start_tone: int = Integer(dump_default=0)
    num_tones: int = Integer(dump_default=22)
    volume: int = Integer(dump_default=16384)
    noise_volume: int = Integer(dump_default=1000)
    bkg_scale: float = Float(dump_default=1/64)
    threshold: float = Float(dump_default=1.5)
    min_connected: int = Integer(dump_default=5)
    hi_clip: float = Float(dump_default=99.9)
    noise_lo: float = Float(dump_default=50)
    noise_hi: float = Float(dump_default=99.9)
    index_sounds: bool = Boolean(dump_default=False)


class SonificationJobSchema(JobSchema):
    type = 'sonification'

    file_id: int = Integer()
    settings: SonificationSettingsSchema = Nested(
        SonificationSettingsSchema, dump_default={})
    format: str = String(dump_default='wav')
