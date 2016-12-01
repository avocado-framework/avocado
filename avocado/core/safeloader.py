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

from ..utils import data_structures


def modules_imported_as(module):
    """
    Returns a mapping of imported module names whether using aliases or not

    The goal of this utility function is to return the name of the import
    as used in the rest of the module, whether an aliased import was used
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


#: Gets the docstring directive value from a string. Used to tweak
#: test class behavior in various ways
AVOCADO_DOCSTRING_DIRECTIVE_RE = re.compile(r'\s*:avocado:\s*(\S+)\s*')


def get_docstring_directive(docstring):
    """
    Returns the value of the avocado docstring directive

    :param docstring: the complete text used as documentation
    :type docstring: str
    """
    if docstring is None:
        return None
    result = AVOCADO_DOCSTRING_DIRECTIVE_RE.search(docstring)
    if result is not None:
        return result.groups()[0]


def is_docstring_directive_enable(docstring):
    """
    Checks if there's a docstring directive that enables a Test class

    :rtype: bool
    """
    result = get_docstring_directive(docstring)
    return result == 'enable'


def is_docstring_directive_disable(docstring):
    """
    Checks if there's a docstring directive that disables a Test class

    :rtype: bool
    """
    result = get_docstring_directive(docstring)
    return result == 'disable'


def is_docstring_directive_tags(docstring):
    """
    Checks if there's a docstring directive that tags a test

    :rtype: bool
    """
    result = get_docstring_directive(docstring)
    if result is not None:
        return result.startswith('tags=')
    return False


def get_docstring_directive_tags(docstring):
    """
    Returns the test categories based on a `:avocado: tags=category` docstring

    :rtype: set
    """
    if not is_docstring_directive_tags(docstring):
        return []

    raw_tag = get_docstring_directive(docstring)
    if raw_tag is not None:
        _, comma_tags = raw_tag.split('tags=', 1)
        return set([tag for tag in comma_tags.split(',') if tag])


def find_class_and_methods(path, method_pattern=None, base_class=None):
    """
    Attempts to find methods names from a given Python source file

    :param path: path to a Python source code file
    :type path: str
    :param method_pattern: compiled regex to match against method name
    :param base_class: only consider classes that inherit from a given
                       base class (or classes that inherit from any class
                       if None is given)
    :type base_class: str or None
    """
    def inherits_from_base_class(class_statement, base_class_name):
        base_ids = [base.id for base in class_statement.bases
                    if hasattr(base, 'id')]
        return base_class_name in base_ids

    result = {}
    mod = ast.parse(open(path).read(), path)
    modules = modules_imported_as(mod)

    for statement in mod.body:
        if isinstance(statement, ast.ClassDef):
            if base_class is not None:
                if not inherits_from_base_class(statement,
                                                base_class):
                    continue
            if method_pattern is None:
                methods = [st.name for st in statement.body if
                           isinstance(st, ast.FunctionDef)]
                methods = data_structures.ordered_list_unique(methods)
            else:
                methods = [st.name for st in statement.body if
                           isinstance(st, ast.FunctionDef) and
                           method_pattern.match(st.name)]
                methods = data_structures.ordered_list_unique(methods)
            result[statement.name] = methods
    return result
