"""
Afterglow Core: pixel operations job plugin
"""

from datetime import datetime
from types import ModuleType
from typing import List as TList

from marshmallow.fields import Integer, List, Nested, String
import numpy
import numpy.fft
import scipy.ndimage as ndimage
import astropy.io.fits as pyfits

from skylib.enhancement.wavelet import wavelet_sharpen
from skylib.color.radio import radio_nat
from skylib.calibration.background import estimate_background
from skylib.calibration.cosmetic import correct_cosmetic, detect_defects

from ...database import db
from ...models import Job, JobResult
from ...schemas import Boolean, Float
from ..data_files import create_data_file, get_data_file_data, get_data_file_fits, get_root, save_data_file


__all__ = ['PixelOpsJob']


class NullBuiltins:
    def __import__(self, *args, **kwargs):
        pass


# Initialize the constant part of the expression evaluation context; disable
# builtins for security reasons
context = {'__builtins__': NullBuiltins()}
# Add numpy and scipy.ndimage non-module defs
for _mod in (numpy, ndimage):
    for _name in _mod.__all__:
        _val = getattr(_mod, _name)
        if not isinstance(_val, ModuleType):
            context[_name] = _val
# Add FFT functions
for _name in ['fft', 'ifft', 'rfft', 'irfft', 'hfft', 'ihfft', 'rfftn',
              'irfftn', 'rfft2', 'irfft2', 'fft2', 'ifft2', 'fftn', 'ifftn']:
    context[_name] = getattr(numpy.fft, _name)
# Keep a reference to numpy as some of its defs are overridden by scipy.ndimage
context['np'] = numpy
# Add some useful SkyLib defs
context['wavelet_sharpen'] = wavelet_sharpen
context['radio_nat'] = radio_nat
context['detect_defects'] = detect_defects
context['correct_cosmetic'] = correct_cosmetic
context['estimate_background'] = lambda *args: estimate_background(*args)[0]
context['estimate_background_rms'] = lambda *args: estimate_background(*args)[1]
context['subtract_background'] = lambda img, *args: img - estimate_background(img, *args)[0]


class PixelOpsJobResult(JobResult):
    file_ids: TList[int] = List(Integer(), dump_default=[])
    data: TList[float] = List(Float(), dump_default=[])


class PixelOpsJob(Job):
    """
    Pixel operations job plugin class

    Operates on a set of input data files. The operation is defined by
    a user-supplied Python expression involving the input image(s) ("img" or
    "imgs[i]") and their FITS headers ("hdr" or "hdrs[i]"). The following
    categories of operations are supported::

        - one output image per input image (e.g. individual image
          transformation like adding a constant or resampling)::
            F(img)  # apply F() to all images, e.g. img = img + 1

        - map all input images to one or more output images::
            F(imgs)  # create a single data file; e.g. sum(imgs, axis=0)
            F(imgs[0], imgs[1], ...)  # apply different operations to all input
                                  # images at once; e.g. (imgs[0], imgs[1] + 1)

        - apply the same operation to multiple sets of input images, resulting
          in a single or multiple output images (e.g. difference images);
          creates as many data files as possible by looping over "i"
          (the difference with the previous case is that the free variable "i"
          must be present in the expression)::
            F(imgs[i], imgs[i+1] ...)  # e.g. imgs[i+1] - imgs[i]

    The expression F() may include any Python operators and constants plus
    Numpy and Scipy.ndimage definitions. It should evaluate either to a 2D
    image or to a scalar. In the latter case, the resulting value is appended
    to PixelOpsJob.result.data. Whether a new data file(s) are created or the
    input ones are replaced by the output 2D image is controlled by the
    `inplace` job parameter; this does not apply to the third case above and if
    F() yields a scalar value. The expression may also include the variables
    "aux_imgs" and "aux_hdrs", which are set to the lists of image data and
    headers for data files listed in the `aux_file_ids` job parameter;
    the first auxiliary image/header is also available via "aux_img" and
    "aux_hdr" variables.
    """
    type = 'pixel_ops'
    description = 'Pixel Operations'

    result: PixelOpsJobResult = Nested(PixelOpsJobResult)
    file_ids: TList[int] = List(Integer(), dump_default=[])
    op: str = String(dump_default=None)
    inplace: bool = Boolean(dump_default=False)
    aux_file_ids: TList[int] = List(Integer(), dump_default=[])

    def run(self):
        # Deduce the type of result by analyzing the user-supplied expression
        expr = self.op
        if not expr or not expr.strip():
            raise ValueError('Missing expression to evaluate')
        expr = expr.strip()
        co = compile(expr, '<op>', 'eval')

        # Load data files
        data_files = [get_data_file_data(self.user_id, file_id)
                      for file_id in self.file_ids]

        local_vars = {}

        # Load optional auxiliary data files
        if getattr(self, 'aux_file_ids', None):
            local_vars['aux_imgs'], local_vars['aux_hdrs'] = tuple(zip(*[
                get_data_file_data(self.user_id, file_id)
                for file_id in self.aux_file_ids]))
            local_vars['aux_img'] = local_vars['aux_imgs'][0]
            local_vars['aux_hdr'] = local_vars['aux_hdrs'][0]
        else:
            local_vars['aux_imgs'], local_vars['aux_hdrs'] = [], []

        if {'imgs', 'hdrs'} & set(co.co_names):
            # Cases 2 and 3; each output must have access to all input images
            if {'img', 'hdr'} & set(co.co_names):
                raise ValueError('Cannot mix "imgs"/"hdrs" with "img"/"hdr"')
            local_vars['imgs'], local_vars['hdrs'] = tuple(zip(*data_files))

            if 'i' in co.co_names:
                # Case 3: mixed input images; evaluate expression and create
                # data file for all possible i's; ignore index errors (e.g.
                # imgs[i+1] - imgs[i] for i = len(imgs) - 1)
                if self.inplace:
                    raise ValueError('inplace=True not allowed with "imgs[i]"')
                for i in range(len(data_files)):
                    local_vars['i'] = i
                    try:
                        self.handle_expr(expr, local_vars, [self.file_ids[i]])
                    except IndexError:
                        pass
                    except Exception as e:
                        self.add_error(e, {'image_no': i})
                    finally:
                        self.update_progress((i + 1)/len(data_files)*100)
            else:
                # Case 2: reduce to a single image/scalar or many-to-many
                # mapping
                self.handle_expr(expr, local_vars, self.file_ids)
        else:
            # Case 1: iterate over all input images
            for i in range(len(data_files)):
                local_vars['img'], local_vars['hdr'] = data_files[i]

                try:
                    self.handle_expr(expr, local_vars, [self.file_ids[i]])
                except Exception as e:
                    self.add_error(e, {'file_id': self.file_ids[i]})
                finally:
                    self.update_progress((i + 1)/len(data_files)*100)

    def handle_expr(self, expr, local_vars, file_ids):
        """
        Evaluate expression for a single output data file

        :param str expr: expression to evaluate (right-hand part only,
            if applicable)
        :param dict local_vars: local definitions: "img", "imgs", "hdr", "hdrs"
        :param list[int | None] file_ids: original data file IDs, used with
            inplace=True

        :return: None
        """
        res = eval(expr, context, local_vars)

        nd = numpy.ndim(res)
        if not nd:
            # Evaluation yields a scalar; append to result
            self.result.data.append(float(res))
            return

        # Evaluation yields one or more arrays
        if nd not in (2, 3):
            raise ValueError(
                'Expression must yield either a scalar or one or multiple 2D '
                'arrays')

        # Convert output to a list of (optionally masked) float32 arrays
        if nd == 2:
            res = [res]
        res = [(data if isinstance(data, numpy.ma.MaskedArray)
                else numpy.asarray(data)).astype(numpy.float32)
               for data in res]

        # Match file IDs to output arrays
        if self.inplace and len(res) != len(file_ids):
            raise ValueError(
                'Number of inputs and outputs must be the same for '
                'inplace=True')
        if len(file_ids) < len(res):
            file_ids = file_ids + [None]*(len(res) - len(file_ids))

        for file_id, data in zip(file_ids, res):
            if file_id is None:
                hdr = pyfits.Header()
                hdr.add_history(
                    '[{}] Created by Afterglow by evaluating '
                    'expression "{}"'.format(datetime.utcnow(), expr))
            else:
                with get_data_file_fits(self.user_id, file_id, read_data=False) as f:
                    hdr = f[0].header
                if self.inplace:
                    hdr.add_history(
                        '[{}] Updated by Afterglow by evaluating expression '
                        '"{}"'.format(datetime.utcnow(), expr))
                else:
                    hdr.add_history(
                        '[{}] Created by Afterglow from data file {:d} by '
                        'evaluating expression "{}"'
                        .format(datetime.utcnow(), file_id, expr))

            try:
                if self.inplace:
                    # Overwrite the existing data file
                    save_data_file(get_root(self.user_id), file_id, data, hdr)
                else:
                    file_id = create_data_file(
                        self.user_id, None, get_root(self.user_id), data, hdr,
                        duplicates='append', session_id=self.session_id).id
                db.session.commit()
            except Exception:
                db.session.rollback()
                raise

            self.result.file_ids.append(file_id)
