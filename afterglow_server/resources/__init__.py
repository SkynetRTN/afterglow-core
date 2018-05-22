"""
Afterglow Access Server: package containing all resources provided by the
server API
"""

import multiprocessing
from . import data_providers, data_files, jobs, photometry, phot_cal

if multiprocessing.current_process().name == 'MainProcess':
    jobs.init_jobs()

del multiprocessing
