#!/usr/bin/env python
from setuptools import setup, find_packages


setup(
    name="ptpdb",
    author="Jonathan Slenders",
    version="0.17",
    url="https://github.com/jonathanslenders/ptpdb",
    description="Python debugger (pdb) build on top of prompt_toolkit",
    long_description="",
    packages=find_packages("."),
    install_requires=["ptpython>=3.0.0", "prompt-toolkit>=3.0.0,<3.1.0",],
)
