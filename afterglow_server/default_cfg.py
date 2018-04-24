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
]


################################################################################
# Data file options
################################################################################

# Root directory for data file storage
DATA_FILE_ROOT = DATA_ROOT

# Per-process data file cache size in megabytes (0 = disable caching)
DATA_FILE_CACHE_SIZE = 0

# Data files authentication; defaults to any method registered in USER_AUTH
DATA_FILE_AUTH = None

# Number of histogram bins or method for calculating the optimal bin size
# ("auto", "fd", "doane", "scott", "rice", "sturges", or "sqrt", see
# https://docs.scipy.org/doc/numpy/reference/generated/numpy.histogram.html)
HISTOGRAM_BINS = 1024
