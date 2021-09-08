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
    version='1.0.1',
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
        'alembic == 1.5.8',
        'Authlib == 0.15.3',
        'astropy == 4.2',
        'astroquery == 0.4.1',
        'email_validator == 1.1.2',
        'ExifRead == 2.3.2',
        'Flask == 1.1.2',
        'Flask_SQLAlchemy == 2.5.1',
        'Flask_Security == 3.0.0',
        'Flask_Cors == 3.0.10',
        'marshmallow == 3.10.0',
        'numpy == 1.20.1',
        'oauthlib == 2.1.0',
        'Pillow == 8.3.2',
        'plaster_pastedeploy == 0.7',
        'pycryptodome == 3.10.1',
        'python_dateutil == 2.8.1',
        'rawpy == 0.16.0',
        'requests == 2.25.1',
        'requests-oauthlib == 1.1.0',
        'scipy == 1.6.1',
        'sep == 1.0.3',
        'SkyLib >= 0.2.0',
        'SQLAlchemy == 1.3.23',
        'Werkzeug == 1.0.1',
        # extra skynet dependencies
        'cryptography == 3.4.6',
        'marshmallow_sqlalchemy == 0.24.2',
        'PyMySQL == 1.0.2',
        'redis == 3.5.3',
        'SQLAlchemy-Utils == 0.36.8',
        'WTForms == 2.3.3',
    ],
    entry_points={
        'paste.app_factory': [
            'main = afterglow_core:main',
        ],
    },
)
