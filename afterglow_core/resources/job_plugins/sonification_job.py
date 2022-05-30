"""
Afterglow Core: image sonification job plugin
"""

import os
import tempfile
import subprocess
import shutil
from io import BytesIO

from marshmallow.fields import String, Integer, Nested

from skylib.calibration.background import estimate_background
from skylib.sonification import sonify_image

from ...models import Job
from ...schemas import AfterglowSchema, Boolean, Float
from ..data_files import get_data_file, get_data_file_data, get_subframe


__all__ = ['SonificationJob']


class SonificationSettings(AfterglowSchema):
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
    bkg_scale: float = Float(dump_default=0.015625)
    threshold: float = Float(dump_default=1.5)
    min_connected: int = Integer(dump_default=5)
    hi_clip: float = Float(dump_default=99.9)
    noise_lo: float = Float(dump_default=50)
    noise_hi: float = Float(dump_default=99.9)
    index_sounds: bool = Boolean(dump_default=False)


class SonificationJob(Job):
    type = 'sonification'
    description = 'Image Sonification'

    file_id: int = Integer()
    settings: SonificationSettings = Nested(
        SonificationSettings, dump_default={})
    format: str = String(dump_default='wav')

    def run(self):
        settings = self.settings
        pixels = get_subframe(
            self.user_id, self.file_id,
            x0=settings.x, y0=settings.y, w=settings.width, h=settings.height)

        x0 = settings.x - 1
        y0 = settings.y - 1

        df = get_data_file(self.user_id, self.file_id)
        height, width = pixels.shape
        if width != df.width or height != df.height:
            # Sonifying a subimage; estimate background from the whole image
            # first, then supply a cutout of background and RMS
            # to sonify_image()
            full_img = get_data_file_data(self.user_id, self.file_id)[0]
            bkg, rms = estimate_background(full_img, size=settings.bkg_scale)
            bkg = bkg[y0:y0+height, x0:x0+width]
            rms = rms[y0:y0+height, x0:x0+width]
        else:
            # When sonifying the whole image, sonify_image() will estimate
            # background automatically
            bkg = rms = None

        data = BytesIO()
        sonify_image(
            pixels, data,
            coord=settings.coord,
            barycenter=settings.barycenter,
            tempo=settings.tempo,
            sampling_rate=settings.sampling_rate,
            start_tone=settings.start_tone,
            num_tones=settings.num_tones,
            volume=settings.volume,
            noise_volume=settings.noise_volume,
            bkg_scale=settings.bkg_scale,
            threshold=settings.threshold,
            min_connected=settings.min_connected,
            hi_clip=settings.hi_clip,
            noise_lo=settings.noise_lo,
            noise_hi=settings.noise_hi,
            bkg=bkg,
            rms=rms,
            index_sounds=settings.index_sounds,
        )
        data = data.getvalue()

        if self.format == 'mp3':
            # Use ffmpeg to convert wav to mp3
            temp_dir = tempfile.mkdtemp(prefix='ffmpeg-')
            try:
                wav_file = os.path.join(temp_dir, 'in.wav')
                mp3_file = os.path.join(temp_dir, 'out.mp3')
                with open(wav_file, 'wb') as f:
                    f.write(data)
                subprocess.check_call(['ffmpeg', '-i', wav_file, mp3_file])
                with open(mp3_file, 'rb') as f:
                    data = f.read()
            finally:
                shutil.rmtree(temp_dir)
            mimetype = 'audio/x-mpeg-3'
        else:
            mimetype = 'audio/x-wav'

        self.create_job_file('sonification', data, mimetype=mimetype)
