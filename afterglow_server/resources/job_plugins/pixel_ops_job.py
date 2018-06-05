"""
Afterglow Access Server: pixel operations job plugin
"""

from __future__ import absolute_import, division, print_function

from types import ModuleType
import numpy
import numpy.fft.fftpack
import scipy.ndimage as ndimage
from astropy.io.fits import PrimaryHDU
from marshmallow.fields import Float, Integer, List, Nested, String
from . import Boolean, Job, JobResult
from ..data_files import (
    SqlaDataFile, create_data_file, get_data_file, get_data_file_db, get_root)


__all__ = ['PixelOpsJob']


# Fixed part of the expression evaluation context; disable builtins for security
# reasons; add numpy and scipy.ndimage non-module defs
context = {'__builtins__': None}
for _mod in (numpy, numpy.fft.fftpack, ndimage):
    for _name in _mod.__all__:
        _val = getattr(_mod, _name)
        if not isinstance(_val, ModuleType):
            context[_name] = _val


class PixelOpsJobResult(JobResult):
    file_ids = List(Integer(), default=[])  # type: list
    data = List(Float(), default=[])  # type: list


class PixelOpsJob(Job):
    """
    Pixel operations job plugin class

    Operates on a set of input data files. The operation is defined by
    a user-supplied Python expression involving the input image(s) ("img" or
    "imgs[i]") and their FITS headers ("hdr" or "hdrs[i]"). The following
    categories of operations are supported::

        - one output image per input image (e.g. individual image transformation
          like adding a constant or resampling)::
            F(img)  # apply F() to all images, e.g. img = img + 1

        - reduce input images into a single output image (e.g. add)::
            F(imgs)  # create a single data file; e.g. sum(imgs)

        - combine input images into multiple output images (e.g. difference
          images); creates as many data files as possible by looping over "i"
          (the difference with the previous case is that the free variable "i"
          must be present in the expression)::
            F(imgs[i], imgs[i+1] ...)  # e.g. imgs[i+1] - imgs[i]

    The expression F() may include any Python operators and constants plus Numpy
    and Scipy.ndimage definitions. It should evaluate either to a 2D image or
    to a scalar. In the latter case, the resulting value is appended
    to PixelOpsJob.result.data. Whether a new data file(s) are created or the
    input ones are replaced by the output 2D image is controlled by the
    `inplace` job parameter; this does not apply to the third case above and if
    F() yields a scalar value.
    """
    name = 'pixel_ops'
    description = 'Pixel Operations'
    result = Nested(PixelOpsJobResult)  # type: PixelOpsJobResult
    file_ids = List(Integer())  # type: list
    op = String()  # type: str
    inplace = Boolean(default=False)  # type: bool

    def run(self):
        # Deduce the type of result by analyzing the user-supplied expression
        expr = self.op
        if not expr or not expr.strip():
            raise ValueError('Missing expression to evaluate')
        expr = expr.strip()
        co = compile(expr, '<op>', 'eval')

        # Load data files
        data_files = [get_data_file(self.user_id, file_id)
                      for file_id in self.file_ids]

        local_vars = {}

        if {'imgs', 'hdrs'} & set(co.co_names):
            # Cases 2 and 3; each output must have access to all input images
            if {'img', 'hdr'} & set(co.co_names):
                raise ValueError('Cannot mix "imgs"/"hdrs" with "img"/"hdr"')
            local_vars['imgs'] = [f[-1].data for f in data_files]
            local_vars['hdrs'] = [f[-1].header for f in data_files]

            if 'i' in co.co_names:
                # Case 3: mixed input images; evaluate expression and create
                # data file for all possible i's; ignore index errors (e.g.
                # imgs[i+1] - imgs[i] for i = len(imgs) - 1)
                if self.inplace:
                    raise ValueError('inplace=True not allowed with "imgs[i]"')
                for i in range(len(data_files)):
                    local_vars['i'] = i
                    try:
                        self.handle_expr(
                            expr, local_vars,
                            self.file_ids[i] if self.file_ids else None)
                    except IndexError:
                        pass
                    except Exception as e:
                        self.add_error('Image #{:d}: {}'.format(i, e))
                    finally:
                        self.state.progress = (i + 1)/len(data_files)
                        self.update()
            else:
                # Case 2: reduce to a single image/scalar; always create a new
                # data file if non-scalar
                self.handle_expr(
                    expr, local_vars,
                    self.file_ids[0] if self.file_ids else None)
        else:
            # Case 1: iterate over all input images
            for i in range(len(data_files)):
                local_vars['img'] = data_files[i][-1].data
                local_vars['hdr'] = data_files[i][-1].header

                try:
                    self.handle_expr(
                        expr, local_vars,
                        self.file_ids[i] if self.file_ids else None)
                except Exception as e:
                    self.add_error(
                        'Data file ID {}: {}'.format(self.file_ids[i], e))
                finally:
                    self.state.progress = (i + 1)/len(data_files)
                    self.update()

    def handle_expr(self, expr, local_vars, file_id=None):
        """
        Evaluate expression for a single output data file

        :param str expr: expression to evaluate (right-hand part only,
            if applicable)
        :param dict local_vars: local definitions: "img", "imgs", "hdr", "hdrs"
        :param int file_id: optional original data file ID

        :return: None
        """
        res = eval(expr, context, local_vars)

        adb = get_data_file_db(self.user_id)

        nd = numpy.ndim(res)
        if nd:
            # Evaluation yields an array; replace the original data file or
            # create a new one
            if nd != 2:
                raise ValueError('Expression must yield 2D array or scalar')
            if self.inplace:
                with get_data_file(self.user_id, file_id, True) as fits:
                    fits[-1].data = numpy.asarray(res).astype(numpy.float32)

                # May need to update the image size
                try:
                    data_file = adb.query(SqlaDataFile).get(file_id)
                    shape = numpy.shape(res)
                    if shape != [data_file.height, data_file.width]:
                        data_file.height, data_file.width = shape
                        adb.commit()
                except Exception:
                    adb.rollback()
                    raise
            else:
                if file_id is None:
                    fits = PrimaryHDU()
                else:
                    fits = get_data_file(self.user_id, file_id)[-1]
                fits.data = res

                try:
                    self.result.file_ids.append(create_data_file(
                        adb, None, fits, get_root(self.user_id),
                        duplicates='append').id)
                    adb.commit()
                except Exception:
                    adb.rollback()
                    raise
        else:
            # Evaluation yields a scalar; append to result
            self.result.data.append(float(res))
