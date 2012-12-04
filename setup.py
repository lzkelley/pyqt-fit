#!/usr/bin/env python

import sys
from setuptools import setup

#from path import path

#with (path(__file__).dirname() / 'pyqt_fit' / 'version.txt').open() as f:
    #__version__ = f.read().strip()

import os.path

version_filename = os.path.join(os.path.dirname(__file__), 'pyqt_fit', 'version.txt')
with open(version_filename, "r") as f:
    __version__ = f.read().strip()

extra = {}
if sys.version_info >= (3,):
    extra['use_2to3'] = True

setup(name='PyQt-Fit',
      version=__version__,
      description='Least-square fitting of user-defined functions',
      author='Pierre Barbier de Reuille',
      author_email='pierre.barbierdereuille@gmail.com',
      url=['https://code.google.com/p/pyqt-fit/'],
      packages= ['pyqt_fit', 'pyqt_fit.functions', 'pyqt_fit.residuals'],
      package_data = {'pyqt_fit': ['qt_fit.ui', 'version.txt']},
      scripts=['bin/pyqt_fit1d.py'],
      requires= [
          'setup_tools',
          'scipy',
          'numpy',
          'cython',
          'pylab',
          'PyQT4',
          'matplotlib',
          'path.py'
          ],
      license = 'LICENSE.txt',
      long_description = open('README.txt').read(),
      classifiers=[
          'Development Status :: 4 - Beta',
          'Environment :: X11 Applications :: Qt',
          'Intended Audience :: Science/Research',
          'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
          'Natural Language :: English',
          'Operating System :: MacOS :: MacOS X',
          'Operating System :: Microsoft :: Windows',
          'Operating System :: POSIX :: Linux',
          'Programming Language :: Python :: 2.7',
          'Topic :: Scientific/Engineering :: Mathematics',
          'Topic :: Scientific/Engineering :: Visualization',
          ],
      **extra
     )

