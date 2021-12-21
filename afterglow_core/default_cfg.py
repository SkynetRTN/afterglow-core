# Default Afterglow Core Configuration

################################################################################
# General
################################################################################
# Prefix URL which will be prepended to all routes
APPLICATION_ROOT = '/core'
DASHBOARD_PREFIX = ''

# Location of the general Afterglow Core data files
DATA_ROOT = '.'


################################################################################
# Security options
################################################################################

AUTH_ENABLED = True

# OAuth Services
#     OAUTH_PLUGINS = [
#         {'name': 'twitter_client_oauth', 'remote_app': 'app',
#          'api_base_url': 'https://api.twitter.com/1/',
#          'access_token_url': 'https://api.twitter.com/oauth/access_token',
#          'authorize_url': 'https://api.twitter.com/oauth/authenticate',
#          'client_id': '<client id>', 'client_secret': '<client secret'}
#     ]
AUTH_PLUGINS = []

# Automatically register authenticated users if missing from the local user
# database; auth plugin option "register_users" overrides this
REGISTER_AUTHENTICATED_USERS = True

# OAuth2 bearer token expiration time in seconds
OAUTH2_PROVIDER_TOKEN_EXPIRES_IN = 3600

# Cookie token expiration time in seconds
COOKIE_TOKEN_EXPIRES_IN = 86400

################################################################################
# Data provider options
################################################################################

# Default data provider auth methods; defaults to any method registered in
# USER_AUTH
DEFAULT_DATA_PROVIDER_AUTH = None

# List of data provider specs [{'name': plugin_name, 'option': option ...} ...]
DATA_PROVIDERS = [
    {'name': 'local_disk', 'display_name': 'Workspace', 'root': DATA_ROOT,
     'readonly': False, 'peruser': True, 'quota': 10 << 30,
     'allow_upload': True},
    {'name': 'imaging_surveys'},
]


################################################################################
# Data file options
################################################################################

# Root directory for data file storage
DATA_FILE_ROOT = DATA_ROOT

# Data files authentication; defaults to any method registered in USER_AUTH
DATA_FILE_AUTH = None

# Allow directly uploading files to Workbench
DATA_FILE_UPLOAD = False

# Number of histogram bins or method for calculating the optimal bin size
# ("auto", "fd", "doane", "scott", "rice", "sturges", or "sqrt", see
# https://docs.scipy.org/doc/numpy/reference/generated/numpy.histogram.html)
HISTOGRAM_BINS = 1024


################################################################################
# Catalog options
################################################################################

# Default VizieR server address for all catalogs; no protocol and path
VIZIER_SERVER = 'vizier.cfa.harvard.edu'

# Cache VizieR queries (may eventually take a lot of disk space)
VIZIER_CACHE = True

# Catalog-specific options:
# CATALOG_OPTIONS = {
#   'APASS': {'vizier_server': 'vizier.u-strasbg.fr',
#             'filter_lookup': {'Open': '0.8*V + 0.2*R'}},
# }
CATALOG_OPTIONS = {}

# Custom VizieR catalog defs:
# CUSTOM_VIZIER_CATALOGS = [
#     {'name': 'NOMAD', 'display_name': 'NOMAD-1', 'num_sources': 1117612732,
#      'vizier_catalog': 'I/297', 'row_limit': 5000,
#      'col_mapping': {
#          'id': 'NOMAD1', 'ra_hours': 'RAJ2000/15', 'dec_degs': 'DEJ2000',
#      },
#      'mags': {'B': 'Bmag', 'V': 'Vmag', 'R': 'Rmag', 'J': 'Jmag', 'H': 'Hmag',
#               'K': 'Kmag'},
#     },
#     ...
# ]
CUSTOM_VIZIER_CATALOGS = []

# Path or list of paths to Astrometry.net index files used for plate solving
# ANET_INDEX_PATH = '/usr/local/astrometry-net/data'
# or
# ANET_INDEX_PATH = ['C:\\Astrometry.net\\data\\Tycho-2',
#                    'C:\\Astrometry.net\\Data\\2MASS']
ANET_INDEX_PATH = []


################################################################################
# Job server options
################################################################################

# TCP port job server listens on
JOB_SERVER_PORT = 2109

# Initial job pool size
JOB_POOL_MIN = 1

# Maximum job pool size; 0 = no limit
JOB_POOL_MAX = 16

# Maximum RAM in megabytes allowed to be allocated by certain memory-intensive
# jobs
JOB_MAX_RAM = 100.0
