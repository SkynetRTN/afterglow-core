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
    entry_points={
        'paste.app_factory': [
            'main = afterglow_core:main',
        ],
    },
)
