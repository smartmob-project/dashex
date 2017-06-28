# -*- coding: utf-8 -*-


from setuptools import find_packages, setup


def readfile(path):
    with open(path, 'rb') as stream:
        return stream.read().decode('utf-8')


readme = readfile('README.rst')
version = readfile('src/dashex/version.txt')


setup(
    name='dashex',
    version='0.0.0',
    maintainer='André Caron',
    maintainer_email='andre.l.caron@gmail.com',
    url='https://github.com/smartmob-project/dashex',
    description='Exchange monitoring dashboard configurations',
    long_description=readme,
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    package_data={
        'dashex': [
            'version.txt',
        ],
    },
    entry_points={
        'console_scripts': [
            'dashex = dashex.__main__:main',
        ],
    },
)
