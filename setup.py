#!/usr/bin/env python

from setuptools import setup
from setuptools import find_packages
from platform import system

import numpy as np
import os

version = '0.0.2'


author = 'Toko Hirono'
author_email = 'hirono@physik.uni-bonn.de'

# requirements for core functionality
install_requires = ['basil-daq', 'bitarray', 'matplotlib', 'numpy', 'pyyaml']

setup(
    name='monopix2_daq',
    version=version,
    description='DAQ for MONOPIX',
    url='https://github.com/SiLab-Bonn/monopix2_daq',
    license='',
    long_description='',
    author=author,
    maintainer=author,
    author_email=author_email,
    maintainer_email=author_email,
    install_requires=install_requires,
    packages=find_packages(),  
    include_package_data=True,  
    package_data={'': ['README.*', 'VERSION'], 'docs': ['*'], 'monopix_daq': ['*.yaml', '*.bit']},
    platforms='any'
)
