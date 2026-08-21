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
# Copyright: 2026 Red Hat, Inc.

"""Prefetch the universal Avocado wheel used by isolated spawners."""

import logging
import sys

from avocado.core.settings import settings
from avocado.core.spawners.wheel_bootstrap import default_wheel_url
from avocado.core.version import VERSION
from avocado.utils.asset import Asset

CACHE_DIRS = settings.as_dict().get("datadir.paths.cache_dirs")

LOG = logging.getLogger("avocado.utils.asset")


def configure_logging_settings():
    LOG.setLevel(logging.INFO)
    logger_handler = logging.StreamHandler()
    LOG.addHandler(logger_handler)
    formatter = logging.Formatter("%(levelname)s: %(message)s")
    logger_handler.setFormatter(formatter)


def main():
    configure_logging_settings()
    url = default_wheel_url(VERSION)
    try:
        asset = Asset(url, cache_dirs=CACHE_DIRS)
        path = asset.fetch()
    except OSError:
        LOG.error("Failed to fetch Avocado wheel from %s", url)
        return 1
    LOG.info("Cached Avocado wheel at %s", path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
