# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: Red Hat Inc. 2022
# Author: Jan Richter <jarichte@redhat.com>

import os

from avocado.core import output
from avocado.core.dependencies.requirements.cache.backends import sqlite
from avocado.core.plugin_interfaces import Cache
from avocado.utils import astring


class RequirementCache(Cache):

    name = "requirement"
    description = "Provides requirement cache entries"

    def list(self):
        environments = sqlite.get_all_requirements()
        requirement_list = ""
        for enviroment_type, requirements in environments.items():
            requirement_list += f"{enviroment_type}:\n"

            requirements_matrix = [
                [
                    requirement["environment"],
                    requirement["requirement_type"],
                    requirement["requirement"],
                ]
                for requirement in requirements
            ]
            header = (
                output.TERM_SUPPORT.header_str("Environment"),
                output.TERM_SUPPORT.header_str("Requirement_type"),
                output.TERM_SUPPORT.header_str("Requirement"),
            )
            requirement_list += "\t" + "\t".join(
                astring.tabular_output(
                    requirements_matrix, header=header, strip=True
                ).splitlines(True)
            )
            requirement_list += "\n\n"
        return requirement_list

    def clear(self):
        if os.path.exists(sqlite.CACHE_DATABASE_PATH):
            os.remove(sqlite.CACHE_DATABASE_PATH)
