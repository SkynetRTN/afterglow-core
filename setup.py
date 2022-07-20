"""
Afterglow Core setuptools setup script
"""

from glob import glob
import fnmatch
from setuptools import setup, find_packages
from setuptools.command.build_py import build_py


module_excludes = [
    'afterglow_core.resources.data_provider_plugins.skynet_local_provider',
]


class BuildPyWithExclude(build_py):
    def find_package_modules(self, package, package_dir):
        modules = super().find_package_modules(package, package_dir)
        return [(pkg, mod, file) for pkg, mod, file in modules
                if not any(fnmatch.fnmatchcase(pkg + '.' + mod, pat=pattern)
                           for pattern in module_excludes)]


setup(
    name='afterglow_core',
    version='1.0.2',
    description='Afterglow Core',
    long_description='A RESTful web service for the processing and analysis '
                     'of astronomical image data.',
    classifiers=[
    ],
    author='Skynet Robotic Telescope Network',
    author_email='vkoupr@email.unc.edu',
    url='https://afterglow.skynet.unc.edu',
    keywords='',
    cmdclass={'build_py': BuildPyWithExclude},
    packages=find_packages() +
    ['afterglow_core.db_migration.' + p + '.versions'
     for p in ('data_files', 'users')],
    include_package_data=True,
    scripts=glob('scripts/*.py'),
    zip_safe=False,
    extras_require={
        'testing': [
            'WebTest >= 1.3.1',  # py3 compat
            'pytest >= 3.7.4',
            'pytest-cov',
        ],
    },
    install_requires=[
        'alembic == 1.7.6',
        'Authlib == 0.15.5',
        'astropy == 4.3.1',
        'astroquery == 0.4.6',
        'email_validator == 1.1.3',
        'ExifRead == 2.3.2',
        'Flask == 2.0.3',
        'Flask_SQLAlchemy == 2.5.1',
        'Flask_Security == 3.0.0',
        'Flask_Cors == 3.0.10',
        'Flask_WTF == 0.14.3',
        'flask-oauthlib == 0.9.6',
        'Jinja2 == 3.0.3',
        'marshmallow == 3.14.1',
        'numpy == 1.22.2',
        'oauthlib == 2.1.0',
        'Pillow == 9.0.1',
        'plaster_pastedeploy == 0.7',
        'portalocker[redis]',
        'pycryptodome == 3.14.1',
        'python_dateutil == 2.8.2',
        'rawpy == 0.17.0',
        'requests == 2.27.1',
        'requests-oauthlib == 1.1.0',
        'scipy == 1.8.0',
        'sep == 1.0.3',
        # 'SkyLib >= 0.2.0',
        'SQLAlchemy == 1.4.31',
        'Werkzeug == 2.0.3',
        # extra skynet dependencies
        'pyslalib',
        'jwt',
        'mysqlclient',
        'cryptography == 36.0.1',
        'marshmallow_sqlalchemy == 0.27.0',
        'PyMySQL == 1.0.2',
        'redis == 4.1.4',
        'SQLAlchemy-Utils == 0.38.2',
        'WTForms == 3.0.1',
    ],
    entry_points={
        'paste.app_factory': [
            'main = afterglow_core:main',
        ],
    },
)
