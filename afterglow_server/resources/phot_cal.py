"""
Afterglow Access Server: photometric calibration of image data files
"""

from __future__ import absolute_import, division, print_function
from marshmallow.fields import Bool
from flask import request
from numpy import array
from .. import Float, Resource, app, errors, json_response, url_prefix
from ..auth import auth_required
from .data_files import get_data_file
from .data_files import get_exp_length, get_gain, get_phot_cal
from .photometry import get_photometry


__all__ = []


class PhotCalSource(Resource):
    mag = Float()
    ref_mag = Float()
    m0 = Float()
    m0_err = Float(allow_none=True)
    rejected = Bool(default=False)


class PhotCal(Resource):
    """
    JSON-serializable photometric calibration parameters

    Attributes::
        m0: photometric zero point
        m0_err: estimated 1-sigma error of `m0`

    """
    m0 = Float()
    m0_err = Float()


@app.route(url_prefix + 'data-files/<int:id>/phot-cal', methods=('GET', 'PUT'))
@auth_required('user')
def data_file_phot_cal(id):
    """
    Request or set data file photometric calibration parameters

    GET /data-files/[id]/phot-cal
        - return PhotCal object for the given image data file; if no photometric
          calibration data are available, the object is empty

    PUT /data-files/[id]/phot-cal?m0=...
        - explicitly set photometric calibration parameters; all parameters not
          set in the query are cleared

    PUT /data-files/[id]/phot-cal
        - initialize photometric calibration from the list of sources or delete
          the current calibration; if request body is empty or contains a JSON
          object that evaluates to False in Python (e.g. empty object), the
          current calibration is deleted; otherwise, the client passes a list
          of calibration sources in the request body as JSON dictionary item
          {"cal_sources": [source, source, ...]}, where source is in either of
          the following formats:
            {"x": x, "y": y, "a": a, ..., "ref_mag": ref_mag}
          where "x", "y", "a", etc. are :func:`afterglow_server.resources.
          photometry.get_photometry` arguments defining the aperture, and
          "ref_mag" is the reference catalog magnitude of the source, or
            {"mag": mag, "ref_mag": ref_mag}
          where "mag" is the measured magnitude of the calibration source.

    :param int id: data file ID

    :return: JSON response containing serialized PhotCal object (possibly empty)
    :rtype: `flask.Response`
    """
    cal_sources = None

    if request.method == 'GET':
        # Get data file header
        hdr = get_data_file(id)[0].header

    else:
        # Update calibration
        with get_data_file(id, update=True) as fits:
            hdr = fits[0].header
            texp = get_exp_length(hdr)
            gain = get_gain(hdr)

            # Remove the current calibration
            for name in list(hdr):
                if name.upper().startswith('PHOT_'):
                    del hdr[name]
            fits.flush()  # otherwise get_photometry() will use the previous cal

            if request.args:
                # Set calibration explicitly
                for name, val in request.args.items():
                    try:
                        val = float(val)
                    except ValueError:
                        try:
                            val = int(val)
                        except ValueError:
                            pass
                    hdr['PHOT_' + name.upper()] = val
            elif request.data and request.is_json and \
                    'cal_sources' in request.json:
                # Initialize calibration from a list of sources and refmags
                sources = []
                for source in request.json['cal_sources']:
                    try:
                        refmag = float(source.pop('ref_mag'))
                    except KeyError:
                        raise errors.MissingFieldError(
                            field='ref_mag',
                            message='Missing cal source reference magnitude')
                    except ValueError:
                        raise errors.ValidationError('ref_mag')

                    try:
                        mag = float(source.pop('mag'))
                    except KeyError:
                        # No magnitude given, measure from image
                        if not all(name in source for name in ('x', 'y', 'a')):
                            raise errors.MissingFieldError(
                                field='x' if 'x' not in source
                                else 'y' if 'y' not in source else 'a')

                        try:
                            source = {name: float(val)
                                      for name, val in source.items()}
                        except ValueError:
                            raise errors.ValidationError(
                                'cal_sources',
                                'Aperture parameters must be floats')

                        try:
                            mag = get_photometry(
                                fits[0].data, texp, gain, {}, **source).mag
                        except TypeError as e:
                            raise errors.ValidationError(
                                'source',
                                e.message if hasattr(e, 'message') and e.message
                                else ', '.join(str(arg) for arg in e.args)
                                if e.args else str(e))
                    except ValueError:
                        raise errors.ValidationError('mag')

                    sources.append((mag, refmag))

                if sources:
                    sources = array(sources)
                    d = sources[:, 1] - sources[:, 0]
                    m0 = d.mean()
                    hdr['PHOT_M0'] = m0, 'Photometric zero point'
                    if len(d) > 1:
                        hdr['PHOT_M0E'] = (
                            d.std(), 'Photometric zero point error')

                    # Create a list of PhotCalSource objects to return
                    cal_sources = []
                    for mag, refmag in sources:
                        s = PhotCalSource()
                        s.mag, s.ref_mag = mag, refmag
                        curr_m0 = s.m0 = refmag - mag
                        if len(sources) > 1:
                            s.m0_err = curr_m0 - m0
                        else:
                            s.m0_err = None
                        cal_sources.append(s)

    res = {'phot_cal': PhotCal(**get_phot_cal(hdr))}
    if cal_sources is not None:
        res['cal_sources'] = cal_sources
    return json_response(res)
