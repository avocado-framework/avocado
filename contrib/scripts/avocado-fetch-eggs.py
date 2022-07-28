#!/bin/env python3
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; specifically version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: 2021 Red Hat, Inc.
# Author: Beraldo Leal <bleal@redhat.com>

import logging
import sys

from avocado.core.settings import settings
from avocado.core.version import VERSION
from avocado.utils.asset import Asset

CACHE_DIRS = settings.as_dict().get("datadir.paths.cache_dirs")

# Avocado asset lib already has its logger. Let's use it.
LOG = logging.getLogger("avocado.utils.asset")


def configure_logging_settings():
    LOG.setLevel(logging.INFO)
    logger_handler = logging.StreamHandler()
    LOG.addHandler(logger_handler)
    formatter = logging.Formatter("%(levelname)s: %(message)s")
    logger_handler.setFormatter(formatter)


def get_egg_url(avocado_version=None, python_version=None):
    if avocado_version is None:
        avocado_version = VERSION
    if python_version is None:
        version = sys.version_info
        python_version = f"{version.major}.{version.minor}"

    asset = f"avocado_framework-{avocado_version}-py{python_version}.egg"
    return f"https://github.com/avocado-framework/avocado/releases/download/{avocado_version}/{asset}"


def main():
    configure_logging_settings()
    for version in ["3.6", "3.7", "3.8", "3.9", "3.10"]:
        url = get_egg_url(python_version=version)
        asset = Asset(url, cache_dirs=CACHE_DIRS)
        asset.fetch()
    return True


if __name__ == "__main__":
    sys.exit(main())
