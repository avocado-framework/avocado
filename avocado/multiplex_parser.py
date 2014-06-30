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
# Copyright: Red Hat Inc. 2014
# Author: Ruda Moura <rmoura@redhat.com>

"""
Module that parses multiplex configurations.
"""

import yaml

def read_yaml(fileobj):
    data = yaml.load(fileobj.read())
    return data

def walk(data, path=None):
    if path is None:
        path = []
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, dict):
                for d in walk(value, path+[key]):
                    yield d
            elif isinstance(value, list):
                for x in value:
                    for d in walk(x, path+[key]):
                        yield path+[key], d
            else:
                yield path, {key: value}
    else:
        yield data
