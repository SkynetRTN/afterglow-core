import os

from setuptools import setup, find_packages


requires = [
    'plaster_pastedeploy',
    'flask',
    'flask_sqlalchemy',
    'flask_security',
    'flask_cors',
    'authlib',
    'pyjwt',
    'sep',
    'marshmallow',
    'numpy',
    'scipy',
    'astropy',
    'astroquery',
    'python-dateutil',
    #skynet dependencies
    'pyjwt',
    'redis',  
    'numpy',
    'scipy',
    'sqlalchemy-utils',
    'pycryptodome',
    'PyMySQL',
    'cryptography',
    'marshmallow',
    'marshmallow_sqlalchemy',
    'astropy'
    'WTForms',
    'email_validator'
    #end skynet dependencies

]

tests_require = [
    'WebTest >= 1.3.1',  # py3 compat
    'pytest >= 3.7.4',
    'pytest-cov',
]

setup(
    name='afterglow_server',
    version='0.0',
    description='Afterglow Server',
    long_description='',
    classifiers=[
    ],
    author='',
    author_email='',
    url='',
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
            'main = afterglow_server:main',
        ],
    },
)




#  'plaster_pastedeploy',
#     'pyramid',
#     'pyramid_jinja2',
#     'pyramid_debugtoolbar',
#     'pyramid_mailer',
#     'pyramid_tm',
#     'pyramid_retry',
#     'waitress',
#     'SQLAlchemy',
#     'WTForms',
#     'bcrypt',
#     # skynet dependencies
#     'pyjwt',
#     'redis',  
#     'numpy',
#     'scipy',
#     'sqlalchemy-utils',
#     'pycryptodome',
#     'PyMySQL',
#     'cryptography',
#     'marshmallow',
#     'marshmallow_sqlalchemy',
#     'astropy'
