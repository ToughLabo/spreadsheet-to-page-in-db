"""Minimal setup file for tasks project."""

from setuptools import setup, find_packages

setup(
    name='spreadsheet_to_page_in_db',
    version='0.1.0',
    license='proprietary',
    description='Module to move data from spreadsheet to notion page',

    author='Kentaro Kajiyama',
    author_email='toughlabo@01-study.com',
    url='',

    packages=find_packages(where='.'),
    package_dir={'': '.'},
)

