"""
Afterglow Core: catalog query job plugin
"""

from typing import Dict as TDict, List as TList, Optional

from marshmallow.fields import String, Integer, List, Nested, Dict
from numpy import argmax, array, cos, deg2rad, r_, rad2deg, unwrap
from numpy.ma import masked_array
from astropy.wcs import WCS

from ...models import Job, JobResult, CatalogSource
from ...schemas import Float
from ..catalogs import catalogs as known_catalogs
from ..data_files import get_data_file_fits


__all__ = ['CatalogQueryJob', 'run_catalog_query_job']


def run_catalog_query_job(job: Job, catalogs: TList[str],
                          ra_hours: Optional[float] = None,
                          dec_degs: Optional[float] = None,
                          radius_arcmins: Optional[float] = None,
                          width_arcmins: Optional[float] = None,
                          height_arcmins: Optional[float] = None,
                          file_ids: Optional[TList[int]] = None,
                          constraints: Optional[TDict[str, str]] = None,
                          source_ids: Optional[TList[str]] = None,
                          skip_failed: bool = False) \
        -> TList[CatalogSource]:
    """
    Catalog query job body; also used during photometric calibration

    :param job: job class instance
    :param catalogs: list of catalog IDs to query
    :param ra_hours: query field centered at this RA; requires `dec_degs`
    :param dec_degs: query field centered at this Dec; requires `ra_hours`
    :param radius_arcmins: query circular area of the given radius centered
        at (`ra_hours`, `dec_degs`); mutually exclusive with `width_arcmins`
        and `height_arcmins`
    :param width_arcmins: query rectangular area of the given width centered
        at (`ra_hours`, `dec_degs`); mutually exclusive with `radius_arcmins`
    :param height_arcmins: query rectangular area of the given height centered
        at (`ra_hours`, `dec_degs`); if omitted, assumed same as
        `width_arcmins`; mutually exclusive with `radius_arcmins`
    :param file_ids: data file IDs to process; if specified, those sources
        are returned that fall into any of the given image FOVs; mutually
        exclusive with the above parameters (`ra_hours`, `dec_degs`,
        `radius_arcmins`, `width_arcmins`, and `height_arcmins`)
    :param constraints: optional catalog-specific constraints in the form
        {"column": "constraint expression", ...}
    :param source_ids: return specific sources; mutually exclusive with all
        other query parameters
    :param skip_failed: ignore data files with no WCS in `file_ids` mode

    :return: list of catalog sources
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
    if not file_ids:
        file_ids = []
    for file_id in file_ids:
        with get_data_file_fits(job.user_id, file_id, read_data=False) as fits:
            try:
                wcs = WCS(fits[0].header, relax=True)
            except Exception:
                if skip_failed:
                    continue
                raise ValueError('Data file ID {} has no WCS'.format(file_id))
            else:
                if wcs.has_celestial:
                    wcs.wcs.crval[0] %= 360
                elif skip_failed:
                    continue
                else:
                    raise ValueError('Invalid WCS for data file ID {}'.format(file_id))
        wcs_list.append(wcs)

    # Calculate bounding box centers and RA/Dec sizes for each of the FOVs
    boxes = []
    for wcs in wcs_list:
        height, width = wcs.array_shape
        center = wcs.all_pix2world((width - 1)/2, (height - 1)/2, 0)
        center[0] %= 360

        # Move center to RA = Dec = 0 so that we get a proper box size in terms
        # of catalog query, i.e. RA size multiplied by cos(dec); the box is
        # guaranteed to intersect RA = 0, so the left boundary is the minimum
        # RA of all four corners above 180, and the right boundary is
        # the maximum RA below 180 (this method formally may not work for
        # highly skewed FOVs close to 360, but this situation is very
        # unlikely); for Decs, the box size is simply the maximum minus
        # the minimum Dec, even if the original field crosses the pole
        wcs0 = wcs.deepcopy()
        wcs0.wcs.crval = [0, 0]
        ras, decs = wcs0.all_pix2world(
            [(0, 0), (width - 1, 0), (width - 1, height - 1), (0, height - 1)],
            0).T
        ras %= 360
        boxes.append((center[0], center[1],
                      ras[ras < 180].max() - ras[ras >= 180].min() + 360,
                      decs.max() - decs.min()))

    if False:  # len(boxes) > 1:
        # A catalog query region represented by its center and width/height is
        # indeed a spherical rectangle bounded by two pairs of parallel great
        # circles; to find the combined region, we first represent them by
        # Lambert rectangles bounded by parallels and meridians, then find their
        # bounding box using algorithm known from GIS, and finally enclose the
        # combined Lambert rectangle in a true spherical rectangle
        lats, lons = [], []
        for ra, dec, width, height in boxes:
            hw, hh = width/2, height/2
            min_dec, max_dec = dec - hh, dec + hh
            if min_dec > 0 or max_dec < 0:
                hw /= max(cos(deg2rad(min_dec)), cos(deg2rad(max_dec)))
            lats += [min_dec, max_dec]
            lons.append(((ra - hw) % 360, (ra + hw) % 360))

        # Use the minimal bounding box algorithm
        min_dec, max_dec = min(lats), max(lats)
        height = max_dec - min_dec
        dec = min_dec + height/2
        xs = array(lons).ravel()
        xs.sort()
        xs = r_[xs, xs[0] + 360]
        biggest_gap = argmax(masked_array(
            xs[1:] - xs[:-1],
            [any(bb[0] <= xs[i] and bb[1] >= xs[i + 1]
                 for bb in rad2deg(unwrap(deg2rad(lons))))
             for i in range(len(xs) - 1)]))
        ra_right, ra_left = xs[biggest_gap:biggest_gap + 2] % 360
        if (ra_left, ra_right) == (0, 360):
            width = 360
        else:
            width = (ra_right - ra_left) % 360
        ra = (ra_left + width/2) % 360
        if min_dec > 0 or max_dec < 0:
            width *= max(cos(deg2rad(min_dec)), cos(deg2rad(max_dec)))

        if width*height > sum(w*h for _, _, w, h in boxes):
            # Individual FOVs are possibly too sparse for a combined FOV to be
            # smaller; fall back to querying them one by one
            ra = dec = width = height = None
    else:
        ra = dec = width = height = None

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

    if width is None:
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
                        if [getattr(s1, name, None) for name in (
                                'id', 'ra_hours', 'dec_degs')] == id:
                            del catalog_sources[j]
                        else:
                            j += 1
                    i += 1

            sources += catalog_sources
    else:
        # Query combined FOV
        for catalog in catalogs:
            sources += known_catalogs[catalog].query_box(
                ra/15, dec, width*60, height*60, constraints)

    # Keep only sources that are within any of the FOVs
    final_sources = []
    for s in sources:
        good = False
        for wcs in wcs_list:
            x, y = wcs.all_world2pix(s.ra_hours*15, s.dec_degs, 0, quiet=True)
            h, w = wcs.array_shape
            if 0 <= x < w and 0 <= y < h:
                good = True
                break
        if good:
            final_sources.append(s)

    return final_sources


class CatalogQueryJobResult(JobResult):
    data: TList[CatalogSource] = List(Nested(CatalogSource), dump_default=[])


class CatalogQueryJob(Job):
    type = 'catalog_query'
    description = 'Catalog Query'

    result: CatalogQueryJobResult = Nested(
        CatalogQueryJobResult, dump_default={})
    catalogs: TList[str] = List(String(), dump_default=[])
    ra_hours: float = Float()
    dec_degs: float = Float()
    radius_arcmins: float = Float()
    width_arcmins: float = Float()
    height_arcmins: float = Float()
    file_ids: TList[int] = List(Integer())
    constraints: TDict[str, str] = Dict(keys=String, values=String)
    source_ids: TList[str] = List(String())

    def run(self):
        object.__setattr__(self.result, 'data', run_catalog_query_job(
            self, catalogs=self.catalogs,
            ra_hours=getattr(self, 'ra_hours', None),
            dec_degs=getattr(self, 'dec_degs', None),
            radius_arcmins=getattr(self, 'radius_arcmins', None),
            width_arcmins=getattr(self, 'width_arcmins', None),
            height_arcmins=getattr(self, 'height_arcmins', None),
            file_ids=getattr(self, 'file_ids', None),
            constraints=getattr(self, 'constraints', None),
            source_ids=getattr(self, 'source_ids', None)))
