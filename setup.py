"""
Afterglow Core setuptools setup script
"""

from setuptools import setup, find_packages


requires = [
    'authlib',
    'astropy',
    'astroquery',
    'email_validator',
    'flask',
    'flask_sqlalchemy',
    'flask_security',
    'flask_cors',
    'marshmallow',
    'numpy',
    'plaster_pastedeploy',
    'pyjwt',
    'python-dateutil',
    'requests',
    'scipy',
    'sep',
    'SQLAlchemy',
    'werkzeug',
    # skynet dependencies
    'cryptography',
    'marshmallow_sqlalchemy',
    'pycryptodome',
    'PyMySQL',
    'redis',
    'sqlalchemy-utils',
    'WTForms',
    #     'pyramid',
    #     'pyramid_jinja2',
    #     'pyramid_debugtoolbar',
    #     'pyramid_mailer',
    #     'pyramid_tm',
    #     'pyramid_retry',
    #     'waitress',
    #     'bcrypt',
    # end skynet dependencies
]

tests_require = [
    'WebTest >= 1.3.1',  # py3 compat
    'pytest >= 3.7.4',
    'pytest-cov',
]

setup(
    name='afterglow_core',
    version='1.0.1',
    description='Afterglow Core',
    long_description='',
    classifiers=[
    ],
    author='',
    author_email='',
    url='afterglow.skynet.unc.edu',
    keywords='',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    extras_require={
        'testing': tests_require,
    },
    install_requires=requires,
    entry_points={
        'paste.app_factory': [
            'main = afterglow_core:main',
        ],
    },
)
