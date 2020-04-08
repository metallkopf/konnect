#!/usr/bin/env python3

from configparser import ConfigParser

from setuptools import find_packages, setup

from konnect import __version__


def requires(section):
  config = ConfigParser()
  config.read("Pipfile")
  return list(config[section].keys())


setup(
  name="konnect",
  version=__version__,
  author="metallkopf",
  description="Headless KDE Connect",
  long_description=open("README.md").read(),
  long_description_content_type="text/markdown",
  url="https://github.com/metallkopf/konnect",
  packages=find_packages(),
  install_requires=requires("packages"),
  extras_require={"dev": requires("dev-packages")},
  classifiers=[
    "Development Status :: 4 - Beta",
    "Environment :: Console",
    "Intended Audience :: Developers",
    "Intended Audience :: System Administrators",
    "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
    "Operating System :: POSIX :: Linux",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.7",
    "Programming Language :: Python :: 3.8",
    "Topic :: Desktop Environment :: K Desktop Environment (KDE)",
    "Topic :: Internet",
    "Topic :: Utilities",
  ],
  keywords="headless kdeconnect kde-connect server",
  python_requires=">=3.7",
  license="GPLv2",
  license_files=["LICENSE.md"],
  entry_points={
    "console_scripts": [
      "konnect=konnect.client:main",
      "konnectd=konnect.server:main",
    ],
  },
)
