# Default Afterglow Access Server Configuration

################################################################################
# General
################################################################################

# Location of the general Afterglow Server data files
DATA_ROOT = '.'


################################################################################
# Security options
################################################################################

# User authentication methods
#     USER_AUTH = None  # no user authentication
#     USER_AUTH = [
#         {'name': 'plugin', 'description': 'My Auth Method',
#          'register_users': False, ...], ...]
#   - enable user auth methods:
# HTTP auth:
#     USER_AUTH = [{'name': 'http'}]
# OAuth2 (client-side flow):
#     USER_AUTH = [
#         {'name': 'twitter_client_oauth', 'remote_app': 'app',
#          'base_url': 'https://api.twitter.com/1/',
#          'access_token_url': 'https://api.twitter.com/oauth/access_token',
#          'authorize_url': 'https://api.twitter.com/oauth/authenticate',
#          'consumer_key': '<client id>', 'consumer_secret': '<client secret'}
#     ]
# OAuth1 (client-side flow):
#   same, add 'request_token_url': ...
USER_AUTH = None

# Automatically register authenticated users if missing from the local user
# database; auth plugin option "register_users" overrides this
REGISTER_AUTHENTICATED_USERS = True

# Allow remote admin access with HTTP user auth enabled
REMOTE_ADMIN = False

# OAuth2 server: list of client descriptions:
#     OAUTH_CLIENTS = [
#         {'name': '<client name>',
#          'description': '<description>',
#          'client_id': '<random string>',
#          'client_secret': '<random string>',
#          'redirect_uris': ['<redirect URI>', ...],
#          'consent_uri': '<consent URI>',
#          'is_confidential': False,
#          'default_scopes': ['email', 'profile', ...],
#          'allowed_grant_types': ['authorization_code'],
#         },
#         ...
#     ]
# All attributes except `name`, `client_id`, `client_secret`, `redirect_uris`,
# and `consent_uri` are optional. OAuth2 server endpoints are not enabled if the
# list is empty.
OAUTH_CLIENTS = []

# OAuth2 error redirect URI
OAUTH2_PROVIDER_ERROR_URI = '/oauth2/errors'

# OAuth2 bearer token expiration time in seconds
OAUTH2_PROVIDER_TOKEN_EXPIRES_IN = 3600


################################################################################
# Data provider options
################################################################################

# Default data provider auth methods; defaults to any method registered in
# USER_AUTH
DEFAULT_DATA_PROVIDER_AUTH = None

# List of data provider specs [{'name': plugin_name, 'option': option ...} ...]
DATA_PROVIDERS = [
    {'name': 'local_disk', 'display_name': 'Workspace', 'root': DATA_ROOT,
     'readonly': False, 'peruser': True, 'quota': 10 << 30},
    {'name': 'imaging_surveys'},
]


################################################################################
# Data file options
################################################################################

# Root directory for data file storage
DATA_FILE_ROOT = DATA_ROOT

# Data files authentication; defaults to any method registered in USER_AUTH
DATA_FILE_AUTH = None

# Number of histogram bins or method for calculating the optimal bin size
# ("auto", "fd", "doane", "scott", "rice", "sturges", or "sqrt", see
# https://docs.scipy.org/doc/numpy/reference/generated/numpy.histogram.html)
HISTOGRAM_BINS = 1024


################################################################################
# Catalog options
################################################################################

# Default VizieR server address for all catalogs; no protocol and path
VIZIER_SERVER = 'vizier.cfa.harvard.edu'

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


################################################################################
# Job server options
################################################################################

# Use encryption (if available) in the message exchange between Flask and job
# server
JOB_SERVER_ENCRYPTION = True

# Initial job pool size
JOB_POOL_MIN = 1

# Maximum job pool size; 0 = no limit
JOB_POOL_MAX = 16
