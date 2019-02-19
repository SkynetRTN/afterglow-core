"""
Afterglow Access Server: catalog query job plugin
"""

from __future__ import absolute_import, division, print_function

from marshmallow.fields import Dict, Integer, List, Nested, String
from astropy.wcs import WCS

from ...data_structures import CatalogSource
from ... import Float
from ..catalogs import catalogs as known_catalogs
from ..data_files import get_data_file_fits
from . import Job, JobResult


__all__ = ['CatalogQueryJob', 'run_catalog_query_job']


def run_catalog_query_job(job, catalogs, ra_hours=None, dec_degs=None,
                          radius_arcmins=None, width_arcmins=None,
                          height_arcmins=None, file_ids=None, constraints=None,
                          source_ids=None):
    """
    Catalog query job body; also used during photometric calibration

    :param Job job: job class instance
    :param list catalogs: list of catalog IDs to query
    :param float ra_hours: query field centered at this RA; requires `dec_degs`
    :param float dec_degs: query field centered at this Dec; requires `ra_hours`
    :param float radius_arcmins: query circular area of the given radius
        centered at (`ra_hours`, `dec_degs`); mutually exclusive with
        `width_arcmins` and `height_arcmins`
    :param float width_arcmins: query rectangular area of the given width
        centered at (`ra_hours`, `dec_degs`); mutually exclusive with
        `radius_arcmins`
    :param float height_arcmins: query rectangular area of the given height
        centered at (`ra_hours`, `dec_degs`); if omitted, assumed same as
        `width_arcmins`; mutually exclusive with `radius_arcmins`
    :param list file_ids: data file IDs to process; if specified, those sources
        are returned that fall into any of the given image FOVs; mutually
        exclusive with the above parameters (`ra_hours`, `dec_degs`,
        `radius_arcmins`, `width_arcmins`, and `height_arcmins`)
    :param dict constraints: optional catalog-specific constraints in the form
        {"column": "constraint expression", ...}
    :param list source_ids: return specific sources; mutually exclusive with all
        other query parameters

    :return: list of catalog sources
    :rtype: list[CatalogSource]
    """
    # Check consistency of query parameters
    if not catalogs:
        raise ValueError('Missing catalog IDs')
    if ra_hours is None:
        if dec_degs is not None:
            raise ValueError('dec_degs assumes ra_hours')
        if not file_ids and not source_ids:
            raise ValueError(
                'Either ra_hours/dec_degs, file_ids, or source_ids are '
                'required')
        if file_ids and source_ids:
            raise ValueError('file_ids is mutually exclusive with source_ids')
        if radius_arcmins is not None:
            raise ValueError('radius_arcmins assumes ra_hours/dec_degs')
        if width_arcmins is not None:
            raise ValueError('width_arcmins assumes ra_hours/dec_degs')
        if height_arcmins is not None:
            raise ValueError('height_arcmins assumes ra_hours/dec_degs')
        if source_ids and constraints:
            raise ValueError('Cannot set constraints for query by source IDs')
    else:
        if dec_degs is None:
            raise ValueError('ra_hours assumes dec_degs')
        if file_ids:
            raise ValueError(
                'file_ids is mutually exclusive with ra_hours/dec_degs')
        if source_ids:
            raise ValueError(
                'source_ids is mutually exclusive with ra_hours/dec_degs')
        if radius_arcmins is None:
            if width_arcmins is None:
                raise ValueError(
                    'Either radius_arcmins or width_arcmins is required')
            if height_arcmins is None:
                height_arcmins = width_arcmins
        elif width_arcmins is not None:
            raise ValueError(
                'width_arcmins is mutually exclusive with radius_arcmins')
        elif height_arcmins is not None:
            raise ValueError(
                'height_arcmins is mutually exclusive with radius_arcmins')

    for catalog in catalogs:
        if catalog not in known_catalogs:
            raise ValueError('Unknown catalog "{}"'.format(catalog))

    sources = []

    if source_ids:
        # Query specific sources by IDs
        for catalog in catalogs:
            sources += known_catalogs[catalog].query_objects(source_ids)
        return sources

    if ra_hours is not None:
        # Query circular or rectangular area
        if radius_arcmins is None:
            for catalog in catalogs:
                sources += known_catalogs[catalog].query_box(
                    ra_hours, dec_degs, width_arcmins, height_arcmins,
                    constraints)
        else:
            for catalog in catalogs:
                sources += known_catalogs[catalog].query_circ(
                    ra_hours, dec_degs, radius_arcmins, constraints)
        return sources

    # Query by file IDs: analyze individual image FOVs to get the combined FOV,
    # which may be more efficient than querying each FOV separately if they
    # overlap
    wcs_list = []
    for file_id in file_ids:
        hdr = get_data_file_fits(job.user_id, file_id)[0].header
        try:
            wcs = WCS(hdr)
        except Exception:
            raise ValueError('Data file ID {} has no WCS'.format(file_id))
        else:
            if not wcs.has_celestial:
                raise ValueError(
                    'Invalid WCS for data file ID {}'.format(file_id))
        wcs_list.append(wcs)

    # Calculate bounding box centers and RA/Dec sizes for each of the FOVs
    boxes = []
    for wcs in wcs_list:
        # noinspection PyProtectedMember
        width, height = wcs._naxis1, wcs._naxis2
        center = wcs.all_pix2world(width/2, height/2, 0)

        # Move center to RA = Dec = 0 so that we get a proper box size in terms
        # of catalog query, i.e. RA size multiplied by cos(dec); the box is
        # guaranteed to intersect RA = 0, so the left boundary is the minimum RA
        # of all four corners above 180, and the right boundary is the maximum
        # RA below 180 (this method formally may not work for highly skewed FOVs
        # close to 360, but this situation is very unlikely); for Decs, the box
        # size is simply the maximum minus the minimum Dec, even if the original
        # field crosses the pole
        wcs0 = wcs.deepcopy()
        wcs0.wcs.crval = [0, 0]
        ras, decs = wcs0.all_pix2world(
            [(0, 0), (width - 1, 0), (width - 1, height - 1), (0, height - 1)],
            0).T
        boxes.append((center[0], center[1],
                      ras[ras < 180].max() - ras[ras >= 180].min() + 360,
                      decs.max() - decs.min()))

    # TODO: Query a single enclosing region if data file FOVs overlap
    # # To obtain the combined FOV, start with the first field
    # total_ra, total_dec, total_ra_width, total_dec_width = boxes[0]
    # for ra, dec, ra_width, dec_width in boxes[1:]:
    #     # Extend the combined FOV; allow Dec to extend beyond the pole to get
    #     # the correct box center and size
    #     hw = total_ra_width/2
    #     total_top, total_bottom = total_dec + hw, total_dec - hw
    #     hw = dec_width/2
    #     top, bottom = dec + hw, dec - hw
    #     if top > total_top:
    #         total_top = top
    #     if bottom < total_bottom:
    #         total_bottom = bottom
    #     total_dec_width = total_top - total_bottom
    #     total_dec = total_top - total_dec_width/2
    #
    #     total_cosd = cos(total_dec*pi/180)
    #     if total_cosd:
    #         hw = total_ra_width/2/total_cosd
    #         if hw >= 180:
    #             total_ra = total_ra_width = 180
    #         else:
    #             total_left = (total_ra - hw) % 360
    #             total_right = (total_ra + hw) % 360
    #             cosd = cos(dec*pi/180)
    #             if cosd:
    #                 hw = ra_width/2/cosd
    #                 left, right = (ra - hw) % 360, (ra + hw) % 360
    #                 if total_left > total_right:
    #                     # Combined FOV crosses 0/360
    #                     if left >= total_left or left <= total_right:
    #                         # Partial overlap
    #                         if right >= total_left or right <= total_right:
    #                             # Combined FOV fully includes current FOV
    #                             continue
    #                         # Extend the right boundary
    #                         total_right = right
    #                     elif right >= total_left or right <= total_right:
    #                         # Partial overlap, extend the left boundary
    #                         total_left = left
    #                     elif left > right:
    #                         # Current FOV fully includes combined FOV
    #                         total_left, total_right = left, right
    #                     else:
    #                         # No overlap; extend either left or right border,
    #                         # depending on which one results in a smaller
    #                         # combined FOV
    #                         pass

    # Query all data file FOVs
    for catalog in catalogs:
        catalog_sources = []
        for ra, dec, width, height in boxes:
            catalog_sources += known_catalogs[catalog].query_box(
                ra/15, dec, width*60, height*60, constraints)

        if len(boxes) > 1 and catalog_sources:
            # Remove duplicates from overlapping fields
            i = 0
            while i < len(catalog_sources):
                s = catalog_sources[i]
                id = [getattr(s, name, None)
                      for name in ('id', 'ra_hours', 'dec_degs')]
                j = i + 1
                while j < len(catalog_sources):
                    s1 = catalog_sources[j]
                    if [getattr(s1, name, None)
                            for name in ('id', 'ra_hours', 'dec_degs')] == id:
                        del catalog_sources[j]
                    else:
                        j += 1
                i += 1

        sources += catalog_sources

    return sources


class CatalogQueryJobResult(JobResult):
    data = List(Nested(CatalogSource), default=[])  # type: list


class CatalogQueryJob(Job):
    name = 'catalog_query'
    description = 'Catalog Query'
    result = Nested(
        CatalogQueryJobResult, default={})  # type: CatalogQueryJobResult
    catalogs = List(String(), default=[])  # type: list
    ra_hours = Float()  # type: float
    dec_degs = Float()  # type: float
    radius_arcmins = Float()  # type: float
    width_arcmins = Float()  # type: float
    height_arcmins = Float()  # type: float
    file_ids = List(Integer())  # type: list
    constraints = Dict(keys=String, values=String)
    source_ids = List(String())  # type: list

    def run(self):
        self.result.data = run_catalog_query_job(
            self, catalogs=self.catalogs,
            ra_hours=getattr(self, 'ra_hours', None),
            dec_degs=getattr(self, 'dec_degs', None),
            radius_arcmins=getattr(self, 'radius_arcmins', None),
            width_arcmins=getattr(self, 'width_arcmins', None),
            height_arcmins=getattr(self, 'height_arcmins', None),
            file_ids=getattr(self, 'file_ids', None),
            constraints=getattr(self, 'constraints', None),
            source_ids=getattr(self, 'source_ids', None))
