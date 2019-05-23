#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages

with open('README.md') as readme_file:
    readme = readme_file.read()

requirements = []

setup_requirements = []

test_requirements = []

setup(
    author="Junjue Wang",
    author_email='junjuew@cs.cmu.edu',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    description="Resource Management Experiments",
    install_requires=requirements,
    license="Apache Software License 2.0",
    long_description=readme + '\n\n',
    include_package_data=True,
    keywords='rmexp',
    name='rmexp',
    packages=find_packages(),
    setup_requires=setup_requirements,
    url='https://github.com/junjuew/resource-management',
    version='0.0.1',
    zip_safe=False,
)
