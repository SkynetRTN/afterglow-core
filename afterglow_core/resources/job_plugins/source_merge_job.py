"""
Afterglow Core: source merge job plugin
"""

from __future__ import annotations

from datetime import datetime
from typing import List as TList, Optional

from marshmallow.fields import List, Nested, String
from numpy import (
    asarray, cos, deg2rad, ndarray, pi, sin, sqrt, transpose, zeros)
from scipy.spatial import cKDTree

from ...models import Job, JobResult, SourceExtractionData
from ...schemas import AfterglowSchema, Float


__all__ = ['SourceMergeJob', 'SourceMergeSettings', 'merge_sources']


def dcs2c(ra: ndarray, dec: ndarray) -> ndarray:
    """
    Convert right ascension and declination to XYZ Cartesian coordinates

    :param ra: right ascension in hours
    :param dec: declination in degrees, same shape as `ra`

    :return: XYZ coordinate(s) of shape shape(ra) + (3,)
    """
    ra, dec = asarray(ra)*pi/12, asarray(dec)*pi/180
    cd = cos(dec)
    return transpose([cos(ra)*cd, sin(ra)*cd, sin(dec)])


def merge_sources(sources: TList[SourceExtractionData],
                  settings: SourceMergeSettings, job_id: Optional[int] = None):
    """
    Find matching sources in multiple images by doing a nearest neighbor match
    using either RA/Dec or XY coordinates, depending on `settings`.pos_type;
    match tolerance is set by `settings`.tol

    :param sources: list of sources to merge
    :param settings: merge settings
    :param job_id: optional job ID included in the merged source IDs

    :return: the same sources in the same order, with
        :class:`SourceExtractionData`.id field set to the same unique value for
        matching sources
    """
    # Set source ID to None before merging
    merged_sources = [SourceExtractionData(source=source, id=None)
                      for source in sources]

    # Split input sources by file ID; save the original source index
    sources_by_file = {}
    for i, source in enumerate(sources):
        sources_by_file.setdefault(getattr(source, 'file_id', None), []).append(
            (i, source))
    if len(sources_by_file) < 2:
        # No data or same file ID for all sources; nothing to merge
        return merged_sources
    if None in sources_by_file:
        raise ValueError('Missing file ID')
    file_ids = list(sorted(sources_by_file))
    n = len(file_ids)

    pos_type = settings.pos_type
    if pos_type not in ('sky', 'pixel', 'auto'):
        raise ValueError(
            'Position type for source merge must be "sky", "pixel", or "auto"')

    tol = settings.tol
    if tol is not None and tol < 0:
        raise ValueError('Match tolerance must be a positive number')

    if pos_type == 'auto':
        if tol:
            raise ValueError(
                'pos_type="auto" implies the automatic merge tolerance')

        # Prefer RA/Decs if all input sources have them
        if all(None not in (source.ra_hours, source.dec_degs)
               for source in sources):
            pos_type = 'sky'
        elif all(None not in (source.x, source.y) for source in sources):
            pos_type = 'pixel'
        else:
            raise ValueError('Missing either RA/Dec or XY for pos_type="auto"')

    if pos_type == 'sky':
        if any(None in (source.ra_hours, source.dec_degs)
               for source in sources):
            raise ValueError('Missing RA/Dec for pos_type="sky"')

        # Use Euclidean metric in 3D for RA/Dec
        coords = [dcs2c(*transpose([(source[1].ra_hours, source[1].dec_degs)
                                    for source in sources_by_file[file_id]]))
                  for file_id in file_ids]
    else:
        if any(None in (source.x, source.y) for source in sources):
            raise ValueError('Missing RA/Dec for pos_type="sky"')

        coords = [[asarray([source[1].x, source[1].y])
                   for source in sources_by_file[file_id]]
                  for file_id in file_ids]

    if not tol:
        # Automatic tolerance is calculated as 0.5 the minimum distance between
        # sources in all images
        min_dist = []
        for coords_for_file in coords:
            nsrc = len(coords_for_file)
            dist_for_file = []
            for i in range(nsrc):
                for j in range(i + 1, nsrc):
                    dist_for_file.append(sqrt(
                        ((coords_for_file[i] - coords_for_file[j])**2).sum()))
            if dist_for_file:
                min_dist.append(min(dist_for_file))
        if not min_dist:
            raise ValueError(
                'Need more than one source in at least some images to use the '
                'automatic merge tolerance')
        tol = 0.5*min(min_dist)
    elif pos_type == 'sky':
        tol = deg2rad(settings.tol)/3600  # arcsecs for pos_type=sky

    # Create k-d trees for each file
    # noinspection PyArgumentList
    trees = [cKDTree(c) for c in coords]
    chains = []
    for i in range(n):
        # Create a (M x N) chain matrix (M = number of sources in the i-th
        # image): its k-th row is a sequence of indices of neighbors to the k-th
        # source in the i-th image for all images (including the i-th one, so
        # CM[k,i] = k); absence of a neighbor in the particular image is
        # indicated by -1
        cm = zeros([len(sources_by_file[file_ids[i]]), n], int)
        for j in range(n):
            cm[:, j] = trees[j].query(coords[i], distance_upper_bound=tol)[1]
            cm[:, j][cm[:, j] == len(sources_by_file[file_ids[j]])] = -1

        # Each row of CM with two or more matches is a new chain
        for chain in cm:
            if (chain >= 0).sum() > 1:
                chains.append(tuple(chain))

    # A merged source is a closed group that occurs in the list of chains
    # exactly as many times as the number of points it contains (non-negative
    # elements in the chain)
    stars = []
    for chain in chains:
        if chain not in stars and chains.count(chain) == n - chain.count(-1):
            stars.append(chain)

    # Generate a unique ID of the form <YYYYMMDDhhmmss>_<job ID>_<source #>
    # for each merged source
    prefix = datetime.utcnow().strftime('%Y%m%d%H%M%S_')
    if job_id:
        prefix += str(job_id) + '_'
    for chain_no, chain in enumerate(stars):
        merged_source_id = prefix + str(chain_no + 1)
        for i, j in enumerate(chain):
            if j != -1:
                source = merged_sources[sources_by_file[file_ids[i]][j][0]]
                source.id = merged_source_id

    return merged_sources


class SourceMergeSettings(AfterglowSchema):
    pos_type: str = String(default='auto')
    tol: float = Float(default=None)


class SourceMergeJobResult(JobResult):
    data: TList[SourceExtractionData] = List(
        Nested(SourceExtractionData), default=[])


class SourceMergeJob(Job):
    type = 'source_merge'
    description = 'Merge Sources from Multiple Images'

    result: SourceMergeJobResult = Nested(SourceMergeJobResult)
    sources: TList[SourceExtractionData] = List(Nested(SourceExtractionData))
    settings: SourceMergeSettings = Nested(SourceMergeSettings, default={})

    def run(self):
        self.result.data = merge_sources(self.sources, self.settings, self.id)
