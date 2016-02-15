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
# Copyright: Red Hat Inc. 2014-2016
# Authors: Cleber Rosa <crosa@redhat.com>

"""
Safe (AST based) test loader module utilities
"""

import ast


def modules_imported_as(module):
    """
    Returns a mapping of imported module names wether using aliases or not

    The goal of this utility function is to return the name of the import
    as used in the rest of the module, wether an aliased import was used
    or not.

    For code such as:

    >>> import foo as bar

    This function should return {"foo": "bar"}

    And for code such as:

    >>> import foo

    It should return {"foo": "foo"}

    Please note that only global level imports are looked at. If there are
    imports defined, say, inside functions or class definitions, they will
    not be seen by this function.

    :param module: module, as parsed by :func:`ast.parse`
    :type module: :class:`_ast.Module`
    :returns: a mapping of names {<realname>: <alias>} of modules imported
    :rtype: dict
    """
    result = {}
    for statement in module.body:
        # Looking for a 'import <module>'
        if isinstance(statement, ast.Import):
            for name in statement.names:
                if name.asname is not None:
                    result[name.name] = name.asname
                else:
                    result[name.name] = name.name
    return result
