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
# Copyright: Red Hat Inc. 2014-2016,2018
# Authors: Cleber Rosa <crosa@redhat.com>
#          Lukas Doktor <ldoktor@redhat.com>

"""
Safe (AST based) test loader module utilities
"""

import ast
import collections
import imp
import json
import os
import re
import sys

from ..utils import data_structures


class PythonModule:
    """
    Representation of a Python module that might contain interesting classes

    By default, it uses module and class names that matches Avocado
    instrumented tests, but it's supposed to be agnostic enough to
    be used for, say, Python unittests.
    """
    __slots__ = ('path', 'klass_imports', 'mod_imports', 'mod', 'imported_objects',
                 'module', 'klass')

    def __init__(self, path, module='avocado', klass='Test'):
        """
        Instantiates a new PythonModule representation

        :param path: path to a Python source code file
        :type path: str
        :param module: the original module name from where the
                       possibly interesting class must have been
                       imported from
        :type module: str
        :param klass: the possibly interesting class original name
        :type klass: str
        """
        self.klass_imports = set()
        self.mod_imports = set()
        if os.path.isdir(path):
            path = os.path.join(path, "__init__.py")
        self.path = path
        self.module = module
        self.klass = klass
        # A dict that keeps track of objects names and importable entities
        #   key => object name from this module point of view
        #   value => Something-like a directory path to the import.
        #            Basically a $path/$module/$variable string, but depending
        #            on the type of import, it can be also be $path/$module.
        self.imported_objects = {}
        with open(self.path) as source_file:
            self.mod = ast.parse(source_file.read(), self.path)

    def is_matching_klass(self, klass):
        """
        Detect whether given class directly defines itself as <module>.<klass>

        It can either be a <klass> that inherits from a test "symbol", like:

        ```class FooTest(Test)```

        Or from an <module>.<klass> symbol, like in:

        ```class FooTest(avocado.Test)```

        :type klass: :class:`_ast.ClassDef`
        :rtype: bool
        """
        # Is it inherited from Test? 'class FooTest(Test):'
        if self.klass_imports:
            base_ids = [base.id for base in klass.bases
                        if isinstance(base, ast.Name)]
            # Looking for a 'class FooTest(Test):'
            if not self.klass_imports.isdisjoint(base_ids):
                return True

        # Is it inherited from avocado.Test? 'class FooTest(avocado.Test):'
        if self.mod_imports:
            for base in klass.bases:
                if not isinstance(base, ast.Attribute):
                    # Check only 'module.Class' bases
                    continue
                cls_module = base.value.id
                cls_name = base.attr
                if cls_module in self.mod_imports and cls_name == self.klass:
                    return True
        return False

    def add_imported_object(self, statement):
        """
        Keeps track of objects names and importable entities
        """
        path = os.path.abspath(os.path.dirname(self.path))
        if getattr(statement, 'module', None) is not None:
            module_path = statement.module.replace('.', os.path.sep)
            path = os.path.join(path, module_path)
        for name in statement.names:
            path = os.path.join(path, name.name.replace('.', os.path.sep))
            if name.asname is None:
                self.imported_objects[name.name] = path
            else:
                self.imported_objects[name.asname] = path

    def _handle_import_from(self, statement):
        self.add_imported_object(statement)
        if statement.module != self.module:
            return
        name = statement_import_as(statement).get(self.klass, None)
        if name is not None:
            self.klass_imports.add(name)

    @staticmethod
    def _all_module_level_names(full_module_name):
        result = []
        components = full_module_name.split(".")[:-1]
        for topmost in range(len(components)):
            result.append(".".join(components[-topmost:]))
            components.pop()
        return result

    def _handle_import(self, statement):
        self.add_imported_object(statement)
        imported_as = statement_import_as(statement)
        name = imported_as.get(self.module, None)
        if name is not None:
            self.mod_imports.add(name)
        for as_name in imported_as.values():
            for mod_name in self._all_module_level_names(as_name):
                if mod_name == self.module:
                    self.mod_imports.add(mod_name)

    def iter_classes(self):
        """
        Iterate through classes and keep track of imported avocado statements
        """
        for statement in self.mod.body:
            # Looking for a 'from <module> import <klass>'
            if isinstance(statement, ast.ImportFrom):
                self._handle_import_from(statement)

            # Looking for a 'import <module>'
            elif isinstance(statement, ast.Import):
                self._handle_import(statement)

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
DOCSTRING_DIRECTIVE_RE_RAW = r'\s*:avocado:[ \t]+(([a-zA-Z0-9]+?[a-zA-Z0-9_:,\=\-\.]*)|(r[a-zA-Z0-9]+?[a-zA-Z0-9_:,\=\{\}\"\-\.\/ ]*))\s*$'
# the RE will match `:avocado: tags=category` or `:avocado: requirements={}`
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


def get_docstring_directives_requirements(docstring):
    """
    Returns the test requirements from docstring patterns like
    `:avocado: requirement={}`.

    :rtype: list
    """
    requirements = []
    for item in get_docstring_directives(docstring):
        if item.startswith('requirement='):
            _, requirement_str = item.split('requirement=', 1)
            try:
                requirements.append(json.loads(requirement_str))
            except json.decoder.JSONDecodeError:
                # ignore requirement in case of malformed dictionary
                continue
    return requirements


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
    :returns: an ordered dictionary with classes as keys and methods as values
    :rtype: collections.OrderedDict
    """
    def inherits_from_base_class(class_statement, base_class_name):
        base_ids = [base.id for base in class_statement.bases
                    if hasattr(base, 'id')]
        return base_class_name in base_ids

    result = collections.OrderedDict()
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


def get_methods_info(statement_body, class_tags, class_requirements):
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

            mt_requirements = get_docstring_directives_requirements(docstring)
            mt_requirements.extend(class_requirements)

            methods = [method for method, _, _ in methods_info]
            if st.name not in methods:
                methods_info.append((st.name, mt_tags, mt_requirements))

    return methods_info


def _determine_match_avocado(module, klass, docstring):
    """
    Implements the match check for Avocado Instrumented Tests
    """
    directives = get_docstring_directives(docstring)
    if 'disable' in directives:
        return True
    if 'enable' in directives:
        return True
    if 'recursive' in directives:
        return True
    # Still not decided, try inheritance
    return module.is_matching_klass(klass)


def _examine_class(path, class_name, match, target_module, target_class,
                   determine_match):
    """
    Examine a class from a given path

    :param path: path to a Python source code file
    :type path: str
    :param class_name: the specific class to be found
    :type path: str
    :param match: whether the inheritance from <target_module.target_class> has
                  been determined or not
    :type match: bool
    :param target_module: the module name under which the target_class lives
    :type target_module: str
    :param target_class: the name of the class that class_name should
                         ultimately inherit from
    :type target_class: str
    :param determine_match: a callable that will determine if a match has
                            occurred or not
    :type determine_match: function
    :returns: tuple where first item is a list of test methods detected
              for given class; second item is set of class names which
              look like avocado tests but are force-disabled.
    :rtype: tuple
    """
    module = PythonModule(path, target_module, target_class)
    info = []
    disabled = set()

    for klass in module.iter_classes():
        if class_name != klass.name:
            continue

        docstring = ast.get_docstring(klass)

        if match is False:
            match = determine_match(module, klass, docstring)

        info = get_methods_info(klass.body,
                                get_docstring_directives_tags(docstring),
                                get_docstring_directives_requirements(
                                    docstring))

        # Getting the list of parents of the current class
        parents = klass.bases

        # From this point we use `_$variable` to name temporary returns
        # from method calls that are to-be-assigned/combined with the
        # existing `$variable`.

        # Searching the parents in the same module
        for parent in parents[:]:
            # Looking for a 'class FooTest(Parent)'
            if not isinstance(parent, ast.Name):
                # 'class FooTest(bar.Bar)' not supported withing
                # a module
                continue
            parent_class = parent.id
            _info, _disabled, _match = _examine_class(module.path, parent_class,
                                                      match, target_module,
                                                      target_class,
                                                      _determine_match_avocado)
            if _info:
                parents.remove(parent)
                info.extend(_info)
                disabled.update(_disabled)
            if _match is not match:
                match = _match

        # If there are parents left to be discovered, they
        # might be in a different module.
        for parent in parents:
            if hasattr(parent, 'value'):
                if hasattr(parent.value, 'id'):
                    # We know 'parent.Class' or 'asparent.Class' and need
                    # to get path and original_module_name. Class is given
                    # by parent definition.
                    _parent = module.imported_objects.get(parent.value.id)
                    if _parent is None:
                        # We can't examine this parent (probably broken
                        # module)
                        continue
                    parent_path = os.path.dirname(_parent)
                    parent_module = os.path.basename(_parent)
                    parent_class = parent.attr
                else:
                    # We don't support multi-level 'parent.parent.Class'
                    continue
            else:
                # We only know 'Class' or 'AsClass' and need to get
                # path, module and original class_name
                _parent = module.imported_objects.get(parent.id)
                if _parent is None:
                    # We can't examine this parent (probably broken
                    # module)
                    continue
                parent_path, parent_module, parent_class = (
                    _parent.rsplit(os.path.sep, 2))

            modules_paths = [parent_path,
                             os.path.dirname(module.path)] + sys.path
            _, found_ppath, _ = imp.find_module(parent_module,
                                                modules_paths)
            _info, _disabled, _match = _examine_class(found_ppath,
                                                      parent_class,
                                                      match,
                                                      target_module,
                                                      target_class,
                                                      _determine_match_avocado)
            if _info:
                info.extend(_info)
                disabled.update(_disabled)
            if _match is not match:
                match = _match

    return info, disabled, match


def find_avocado_tests(path):
    """
    Attempts to find Avocado instrumented tests from Python source files

    :param path: path to a Python source code file
    :type path: str
    :returns: tuple where first item is dict with class name and additional
              info such as method names and tags; the second item is
              set of class names which look like avocado tests but are
              force-disabled.
    :rtype: tuple
    """
    module_name = 'avocado'
    class_name = 'Test'

    module = PythonModule(path, module_name, class_name)
    # The resulting test classes
    result = collections.OrderedDict()
    disabled = set()

    for klass in module.iter_classes():
        docstring = ast.get_docstring(klass)
        # Looking for a class that has in the docstring either
        # ":avocado: enable" or ":avocado: disable
        if check_docstring_directive(docstring, 'disable'):
            disabled.add(klass.name)
            continue

        if check_docstring_directive(docstring, 'enable'):
            info = get_methods_info(klass.body,
                                    get_docstring_directives_tags(docstring),
                                    get_docstring_directives_requirements(
                                        docstring))
            result[klass.name] = info
            continue

        # From this point onwards we want to do recursive discovery, but
        # for now we don't know whether it is avocado.Test inherited
        # (Ifs are optimized for readability, not speed)

        # If "recursive" tag is specified, it is forced as Avocado test
        if check_docstring_directive(docstring, 'recursive'):
            is_avocado = True
        else:
            is_avocado = module.is_matching_klass(klass)
        info = get_methods_info(klass.body,
                                get_docstring_directives_tags(docstring),
                                get_docstring_directives_requirements(
                                    docstring))
        _disabled = set()

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
            _info, _dis, _avocado = _examine_class(module.path, parent_class,
                                                   is_avocado, module_name,
                                                   class_name,
                                                   _determine_match_avocado)
            if _info:
                parents.remove(parent)
                info.extend(_info)
                _disabled.update(_dis)
            if _avocado is not is_avocado:
                is_avocado = _avocado

        # If there are parents left to be discovered, they
        # might be in a different module.
        for parent in parents:
            if hasattr(parent, 'value'):
                if hasattr(parent.value, 'id'):
                    # We know 'parent.Class' or 'asparent.Class' and need
                    # to get path and original_module_name. Class is given
                    # by parent definition.
                    _parent = module.imported_objects.get(parent.value.id)
                    if _parent is None:
                        # We can't examine this parent (probably broken
                        # module)
                        continue
                    parent_path = os.path.dirname(_parent)
                    parent_module = os.path.basename(_parent)
                    parent_class = parent.attr
                else:
                    # We don't support multi-level 'parent.parent.Class'
                    continue
            else:
                # We only know 'Class' or 'AsClass' and need to get
                # path, module and original class_name
                _parent = module.imported_objects.get(parent.id)
                if _parent is None:
                    # We can't examine this parent (probably broken
                    # module)
                    continue
                parent_path, parent_module, parent_class = (
                    _parent.rsplit(os.path.sep, 2))

            modules_paths = [parent_path,
                             os.path.dirname(module.path)] + sys.path
            try:
                _, found_ppath, _ = imp.find_module(parent_module, modules_paths)
            except ImportError:
                continue
            _info, _dis, _avocado = _examine_class(found_ppath,
                                                   parent_class,
                                                   is_avocado,
                                                   module_name,
                                                   class_name,
                                                   _determine_match_avocado)
            if _info:
                info.extend(_info)
                _disabled.update(_dis)
            if _avocado is not is_avocado:
                is_avocado = _avocado

        # Only update the results if this was detected as 'avocado.Test'
        if is_avocado:
            result[klass.name] = info
            disabled.update(_disabled)

    return result, disabled


def _determine_match_unittest(module, klass,
                              docstring):  # pylint: disable=W0613
    """
    Implements the match check for Python Unittests
    """
    return module.is_matching_klass(klass)


def find_python_unittests(path):
    """
    Attempts to find methods names from a given Python source file

    This is a simpler, albeit more strict and correct, alternative version to
    :func:`find_class_and_methods`, in the sense that it checks for the
    (immediate) module name base class name.

    :param path: path to a Python source code file
    :type path: str
    :returns: an ordered dictionary with classes as keys and methods as values
    :rtype: collections.OrderedDict
    """
    module_name = 'unittest'
    class_name = 'TestCase'

    module = PythonModule(path, module_name, class_name)
    result = collections.OrderedDict()

    for klass in module.iter_classes():
        docstring = ast.get_docstring(klass)
        parents = klass.bases
        is_unittest = module.is_matching_klass(klass)

        info = get_methods_info(klass.body,
                                get_docstring_directives_tags(docstring),
                                get_docstring_directives_requirements(
                                    docstring))

        # Searching the parents in the same module
        for parent in parents[:]:
            # Looking for a 'class FooTest(Parent)'
            if not isinstance(parent, ast.Name):
                # 'class FooTest(bar.Bar)' not supported within a module
                continue
            parent_class = parent.id
            _info, _dis, _is_unittest = _examine_class(module.path, parent_class,
                                                       is_unittest, module_name,
                                                       class_name,
                                                       _determine_match_unittest)
            if _info:
                parents.remove(parent)
                info.extend(_info)
            if _is_unittest is not is_unittest:
                is_unittest = _is_unittest

        # If there are parents left to be discovered, they
        # might be in a different module.
        for parent in parents:
            if hasattr(parent, 'value'):
                if hasattr(parent.value, 'id'):
                    # We know 'parent.Class' or 'asparent.Class' and need
                    # to get path and original_module_name. Class is given
                    # by parent definition.
                    _parent = module.imported_objects.get(parent.value.id)
                    if _parent is None:
                        # We can't examine this parent (probably broken
                        # module)
                        continue
                    parent_path = os.path.dirname(_parent)
                    parent_module = os.path.basename(_parent)
                    parent_class = parent.attr
                else:
                    # We don't support multi-level 'parent.parent.Class'
                    continue
            else:
                # We only know 'Class' or 'AsClass' and need to get
                # path, module and original class_name
                _parent = module.imported_objects.get(parent.id)
                if _parent is None:
                    # We can't examine this parent (probably broken
                    # module)
                    continue
                parent_path, parent_module, parent_class = (
                    _parent.rsplit(os.path.sep, 2))

            modules_paths = [parent_path,
                             os.path.dirname(module.path)] + sys.path
            try:
                _, found_ppath, _ = imp.find_module(parent_module, modules_paths)
            except ImportError:
                continue
            _info, _dis, _is_unittest = _examine_class(found_ppath,
                                                       parent_class,
                                                       is_unittest,
                                                       module_name,
                                                       class_name,
                                                       _determine_match_unittest)
            if _info:
                info.extend(_info)
            if _is_unittest is not is_unittest:
                is_unittest = _is_unittest

        # Only update the results if this was detected as 'avocado.Test'
        if is_unittest:
            result[klass.name] = info

    return result
