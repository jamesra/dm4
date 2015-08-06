'''
Created on July 30th, 2015

@author: James Anderson
'''

import glob
import os

from setuptools import setup, find_packages

from ez_setup import use_setuptools


# This if test prevents an infinite recursion running tests from "python setup.py test"
if __name__ == '__main__':

    use_setuptools()

    install_requires = []

    packages = find_packages()

    provides = ["dm4reader"]

    dependency_links = []

    package_dir = {'dm4reader' : 'dm4reader'}
    
    #scripts = glob.glob(os.path.join('scripts', '*.py'))

    #cmdFiles = glob.glob(os.path.join('scripts', '*.cmd'))

    #scripts.extend(cmdFiles)

    #entry_points = {'console_scripts': ['dmdumptags = dmreader.build:Execute']}

    setup(name='dm4reader',
          zip_safe=True,
          version='1.0.0',
          #scripts=scripts,
          description="Digital Micrograph 4 file reader",
          author="James Anderson",
          author_email="James.R.Anderson@utah.edu",
          url="https://nornir.github.io/",
          packages=packages,
          #entry_points=entry_points,
          install_requires=install_requires,
          provides=provides,
          test_suite="test",
          dependency_links=dependency_links)
