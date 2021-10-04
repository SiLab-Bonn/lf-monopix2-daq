#!/usr/bin/env python

from setuptools import setup
from setuptools import find_packages
from platform import system

import numpy as np
import os

version = '0.0.1'


author = 'Ivan Caicedo, Tomasz Hemperek, Toko Hirono'
author_email = 'caicedo@physik.uni-bonn.de'

# requirements for core functionality
install_requires = ['bitarray', 'matplotlib', 'numba', 'numpy', 'pyyaml', 'scipy', 'tables', 'tqdm']

setup(
    name='monopix2_daq',
    version=version,
    description='DAQ for the LF-Monopix2 DMAPS prototype',
    url='https://github.com/SiLab-Bonn/lf-monopix2-daq/',
    license='',
    long_description='',
    author=author,
    maintainer=author,
    author_email=author_email,
    maintainer_email=author_email,
    install_requires=install_requires,
    python_requires=">=3.0",
    packages=find_packages(),  
    include_package_data=True,  
    package_data={'': ['README.*', 'VERSION'], 'docs': ['*'], 'monopix_daq': ['*.yaml', '*.bit']},
    platforms='any'
)
