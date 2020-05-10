"""
Afterglow Core setuptools setup script
"""

from setuptools import setup, find_packages

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
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    extras_require={
        'testing': [
            'WebTest >= 1.3.1',  # py3 compat
            'pytest >= 3.7.4',
            'pytest-cov',
        ],
    },
    install_requires=[
        'alembic == 1.4.2',
        'Authlib == 0.14.2',
        'astropy == 4.0.1',
        'astroquery == 0.4',
        'email_validator == 1.1.0',
        'ExifRead == 2.1.2',
        'Flask == 1.1.2',
        'Flask_SQLAlchemy == 2.4.1',
        'Flask_Security == 3.0.0',
        'Flask_Cors == 3.0.8',
        'marshmallow == 3.6.0',
        'numpy == 1.18.4',
        'Pillow == 7.1.2',
        'plaster_pastedeploy == 0.7',
        'pycryptodome == 3.9.7',
        'PyJWT == 1.7.1',
        'python_dateutil == 2.8.1',
        'rawpy == 0.14.0',
        'requests == 2.23.0',
        'scipy == 1.4.1',
        'sep == 1.0.3',
        'SkyLib == 0.1.3',
        'SQLAlchemy == 1.3.16',
        'Werkzeug == 1.0.1',
        # extra skynet dependencies
        'cryptography == 2.9.2',
        'marshmallow_sqlalchemy == 0.23.0',
        'PyMySQL == 0.9.3',
        'redis == 3.5.0',
        'SQLAlchemy-Utils == 0.36.5',
        'WTForms == 2.3.1',
    ],
    entry_points={
        'paste.app_factory': [
            'main = afterglow_core:main',
        ],
    },
)
