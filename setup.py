#!/usr/bin/env python
import os
from setuptools import find_packages, setup
import warnings


def parse_requirements(filename):
  """ Parse a requirements file ignoring comments and -r inclusions of other files """
  reqs = []
  with open(filename, 'r') as f:
    for line in f:
      hash_idx = line.find('#')
      if hash_idx >= 0:
        line = line[:hash_idx]
      line = line.strip()
      if line:
        reqs.append(line)
  return reqs


with open('README.md', 'r') as f:
  readme = f.read().strip()


setup(
  name="SUSO",
  version='0.0.1',
  url="https://github.com/thelabdc/OVSJG-SUSO",
  author="The Lab @ DC",
  author_email="the.lab@dc.gov",
  license="Proprietary",
  packages=find_packages(),
  include_package_data=True,
  install_requires=parse_requirements('requirements.txt'),
  tests_require=parse_requirements('requirements.testing.txt'),
  description="Tools for the OVSJG SUSO project",
  entry_points={
    'console_scripts': ['susocli=suso.cli:cli']
  },
  long_description="\n" + readme
)
