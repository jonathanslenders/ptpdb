#!/usr/bin/env python
from setuptools import setup


setup(
        name='ptpdb',
        author='Jonathan Slenders',
        version='0.1',
        url='https://github.com/jonathanslenders/ptpdb',
        description='Python debugger (pdb) build on top of prompt_toolkit',
        long_description='',
        install_requires = [
            'prompt_toolkit',
        ],
)
