#!/usr/bin/env python
import os
from setuptools import setup, find_packages

long_description = open(
    os.path.join(
        os.path.dirname(__file__),
        'README.md'
    )
).read()


setup(
    name='pthy',
    author='Adam Schwalm',
    version='0.1',
    url='https://github.com/alschwam/pthy',
    description='A better hy REPL',
    long_description=long_description,
    packages=find_packages('.'),
    install_requires=[
        'prompt_toolkit>=0.47',
        'jedi>=0.9.0',
    ],
    entry_points={
        'console_scripts': [
            'pthy = pthy.pthy:main',
        ]
    }
)
