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
import collections
import imp
import os
import re
import sys

from ..utils import data_structures


class AvocadoModule(object):
    """
    Representation of a module that might contain avocado.Test tests
    """
    __slots__ = 'path', 'test_imports', 'mod_imports', 'mod'

    def __init__(self, path):
        self.path = path
        self.test_imports = set()
        self.mod_imports = set()
        if os.path.isdir(path):
            self.path = os.path.join(path, "__init__.py")
        else:
            self.path = path
        with open(self.path) as source_file:
            self.mod = ast.parse(source_file.read(), self.path)

    def iter_classes(self):
        """
        Iterate through classes and keep track of imported avocado statements
        """
        for statement in self.mod.body:
            # Looking for a 'from avocado import Test'
            if (isinstance(statement, ast.ImportFrom) and
                    statement.module == 'avocado'):

                for name in statement.names:
                    if name.name == 'Test':
                        if name.asname is not None:
                            self.test_imports.add(name.asname)
                        else:
                            self.test_imports.add(name.name)
                        break

            # Looking for a 'import avocado'
            elif isinstance(statement, ast.Import):
                imp_name = statement_import_as(statement).get('avocado', None)
                if imp_name is not None:
                    self.mod_imports.add(imp_name)

            # Looking for a 'class Anything(anything):'
            elif isinstance(statement, ast.ClassDef):
                yield statement


def statement_import_as(statement):
    """
    Returns a mapping of imported module names whether using aliases or not

    :param statement: an AST import statement
    :type statement: ast.Import
    :returns: a mapping of names {<realname>: <alias>} of modules imported
    :rtype: dict
    """
    result = {}
    for name in statement.names:
        if name.asname is not None:
            result[name.name] = name.asname
        else:
            result[name.name] = name.name
    return result


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
        if isinstance(statement, ast.Import):
            result.update(statement_import_as(statement))
    return result


#: Gets the docstring directive value from a string. Used to tweak
#: test behavior in various ways
DOCSTRING_DIRECTIVE_RE_RAW = r'\s*:avocado:[ \t]+([a-zA-Z0-9]+?[a-zA-Z0-9_:,\=]*)\s*$'
DOCSTRING_DIRECTIVE_RE = re.compile(DOCSTRING_DIRECTIVE_RE_RAW)


def get_docstring_directives(docstring):
    """
    Returns the values of the avocado docstring directives

    :param docstring: the complete text used as documentation
    :type docstring: str

    :rtype: builtin.list
    """
    result = []
    if docstring is None:
        return result
    for line in docstring.splitlines():
        try:
            match = DOCSTRING_DIRECTIVE_RE.match(line)
            if match:
                result.append(match.groups()[0])
        except TypeError:
            pass
    return result


def check_docstring_directive(docstring, directive):
    """
    Checks if there's a given directive in a given docstring

    :rtype: bool
    """
    return directive in get_docstring_directives(docstring)


def get_docstring_directives_tags(docstring):
    """
    Returns the test categories based on a `:avocado: tags=category`
    docstring

    :rtype: dict
    """
    result = {}
    for item in get_docstring_directives(docstring):
        if item.startswith('tags='):
            _, comma_tags = item.split('tags=', 1)
            for tag in comma_tags.split(','):
                if not tag:
                    continue
                if ':' in tag:
                    key, val = tag.split(':', 1)
                    if key in result:
                        result[key].add(val)
                    else:
                        result[key] = set([val])
                else:
                    result[tag] = None
    return result


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
    with open(path) as source_file:
        mod = ast.parse(source_file.read(), path)

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


def get_methods_info(statement_body, class_tags):
    """
    Returns information on an Avocado instrumented test method
    """
    methods_info = []
    for st in statement_body:
        if (isinstance(st, ast.FunctionDef) and
                st.name.startswith('test')):
            docstring = ast.get_docstring(st)
            mt_tags = get_docstring_directives_tags(docstring)
            mt_tags.update(class_tags)

            methods = [method for method, _ in methods_info]
            if st.name not in methods:
                methods_info.append((st.name, mt_tags))

    return methods_info


def find_avocado_tests(path, class_name=None):
    """
    Attempts to find Avocado instrumented tests from Python source files

    :param path: path to a Python source code file
    :type path: str
    :param class_name: the specific class to be found
    :type path: str
    :returns: tuple where first item is dict with class name and additional
              info such as method names and tags; the second item is
              set of class names which look like avocado tests but are
              force-disabled.
    :rtype: tuple
    """
    module = AvocadoModule(path)
    # The resulting test classes
    result = collections.OrderedDict()
    disabled = set()

    for klass in module.iter_classes():
        # class_name will exist only under recursion. In that
        # case, we will only process the class if it has the
        # expected class_name.
        if class_name is not None and class_name != klass.name:
            continue

        docstring = ast.get_docstring(klass)
        # Looking for a class that has in the docstring either
        # ":avocado: enable" or ":avocado: disable
        has_disable = check_docstring_directive(docstring,
                                                'disable')
        if (has_disable and class_name is None):
            disabled.add(klass.name)
            continue

        cl_tags = get_docstring_directives_tags(docstring)

        has_enable = check_docstring_directive(docstring,
                                               'enable')
        if (has_enable and class_name is None):
            info = get_methods_info(klass.body, cl_tags)
            result[klass.name] = info
            continue

        # Looking for the 'recursive' docstring or a 'class_name'
        # (meaning we are under recursion)
        has_recurse = check_docstring_directive(docstring,
                                                'recursive')
        if (has_recurse or class_name is not None):
            info = get_methods_info(klass.body, cl_tags)
            result[klass.name] = info

            # Getting the list of parents of the current class
            parents = klass.bases

            # Searching the parents in the same module
            for parent in parents[:]:
                # Looking for a 'class FooTest(Parent)'
                if not isinstance(parent, ast.Name):
                    # 'class FooTest(bar.Bar)' not supported withing
                    # a module
                    continue
                parent_class = parent.id
                res, dis = find_avocado_tests(path, parent_class)
                if res:
                    parents.remove(parent)
                    for cls in res:
                        info.extend(res[cls])
                disabled.update(dis)

            # If there are parents left to be discovered, they
            # might be in a different module.
            for parent in parents:
                if isinstance(parent, ast.Attribute):
                    # Looking for a 'class FooTest(module.Parent)'
                    parent_module = parent.value.id
                    parent_class = parent.attr
                else:
                    # Looking for a 'class FooTest(Parent)'
                    parent_module = None
                    parent_class = parent.id

                for node in module.mod.body:
                    reference = None
                    # Looking for 'from parent import class'
                    if isinstance(node, ast.ImportFrom):
                        reference = parent_class
                    # Looking for 'import parent'
                    elif isinstance(node, ast.Import):
                        reference = parent_module

                    if reference is None:
                        continue

                    for artifact in node.names:
                        # Looking for a class alias
                        # ('from parent import class as alias')
                        if artifact.asname is not None:
                            parent_class = reference = artifact.name
                        # If the parent class or the parent module
                        # is found in the imports, discover the
                        # parent module path and find the parent
                        # class there
                        if artifact.name == reference:
                            modules_paths = [os.path.dirname(path)]
                            modules_paths.extend(sys.path)
                            if parent_module is None:
                                parent_module = node.module
                            mod_file, ppath, _ = imp.find_module(parent_module,
                                                                 modules_paths)
                            if mod_file is not None:
                                mod_file.close()
                            res, dis = find_avocado_tests(ppath,
                                                          parent_class)
                            if res:
                                for cls in res:
                                    info.extend(res[cls])
                            disabled.update(dis)

            continue

        # Looking for a 'class FooTest(Test):'
        if module.test_imports:
            base_ids = [base.id for base in klass.bases
                        if isinstance(base, ast.Name)]
            # Looking for a 'class FooTest(Test):'
            if not module.test_imports.isdisjoint(base_ids):
                info = get_methods_info(klass.body,
                                        cl_tags)
                result[klass.name] = info
                continue

        # Looking for a 'class FooTest(avocado.Test):'
        if module.mod_imports:
            for base in klass.bases:
                if not isinstance(base, ast.Attribute):
                    # Check only 'module.Class' bases
                    continue
                cls_module = base.value.id
                cls_name = base.attr
                if cls_module in module.mod_imports and cls_name == 'Test':
                    info = get_methods_info(klass.body,
                                            cl_tags)
                    result[klass.name] = info
                    continue

    return result, disabled
