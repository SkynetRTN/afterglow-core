"""
Afterglow Access Server: API version info
"""

__version__ = 1, 0

url_prefix = '/api/v{0[0]}.{0[1]}/'.format(__version__[:2])
