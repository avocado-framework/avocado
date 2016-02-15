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
import re


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


#: Gets the tag value from a string. Used to tag a test class in various ways
AVOCADO_DOCSTRING_TAG_RE = re.compile(r'\s*:avocado:\s*(\S+)\s*')


def get_docstring_tag(docstring):
    """
    Returns the value of the avocado custom tag inside a docstring

    :param docstring: the complete text used as documentation
    :type docstring: str
    """
    if docstring is None:
        return None
    result = AVOCADO_DOCSTRING_TAG_RE.search(docstring)
    if result is not None:
        return result.groups()[0]


def is_docstring_tag_enable(docstring):
    """
    Checks if there's an avocado tag that enables its class as a Test class

    :rtype: bool
    """
    result = get_docstring_tag(docstring)
    return result == 'enable'


def is_docstring_tag_disable(docstring):
    """
    Checks if there's an avocado tag that disables its class as a Test class

    :rtype: bool
    """
    result = get_docstring_tag(docstring)
    return result == 'disable'
