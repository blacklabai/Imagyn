# -*- coding: utf-8 -*-
"""
Created on Sun Feb  3 13:22:18 2019

@author: Rupert.Thomas
"""

#from distutils.core import setup
from setuptools import setup
from os import path

# read the contents of README file
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'Readme.md'), encoding='utf-8') as f:
    long_description = f.read()
    
setup(
    name='imagyn',
    version='0.1dev',
    packages=['imagyn', 'imagyn.collection', 'imagyn.synthesis'],
    license='MIT',
    author='Zev Isert; Jose Gordillo; Matt Hodgson; Graeme Turney; Maxwell Borden',
    long_description=long_description,
    install_requires=[
        "pillow",
        "nltk",
        "scikit-image",
    ],
)