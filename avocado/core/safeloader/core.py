import ast
import collections
import sys
from importlib.machinery import PathFinder

from avocado.core.safeloader.docstring import (
    check_docstring_directive, get_docstring_directives,
    get_docstring_directives_dependencies, get_docstring_directives_tags)
from avocado.core.safeloader.module import PythonModule


def get_methods_info(statement_body, class_tags, class_dependencies):
    """Returns information on test methods.

    :param statement_body: the body of a "class" statement
    :param class_tags: the tags at the class level, to be combined with the
                       tags at the method level.
    :param class_dependencies: the dependencies at the class level, to be
                               combined with the dependencies at the method
                               level.
    """
    methods_info = []
    for st in statement_body:
        if not (isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef))):
            continue

        decorators = getattr(st, 'decorator_list', [])
        decorator_names = [getattr(_, 'id', None) for _ in decorators]
        if 'property' in decorator_names:
            continue

        if not st.name.startswith('test'):
            continue

        docstring = ast.get_docstring(st)

        mt_tags = get_docstring_directives_tags(docstring)
        mt_tags.update(class_tags)

        mt_dependencies = get_docstring_directives_dependencies(docstring)
        mt_dependencies.extend(class_dependencies)

        methods = [method for method, _, _ in methods_info]
        if st.name not in methods:
            methods_info.append((st.name, mt_tags, mt_dependencies))

    return methods_info


def _extend_test_list(current, new):
    for test in new:
        test_method_name = test[0]
        if test_method_name not in [_[0] for _ in current]:
            current.append(test)


def _examine_same_module(parents, info, disabled, match, module,
                         target_module, target_class, determine_match):
    # Searching the parents in the same module
    for parent in parents[:]:
        # Looking for a 'class FooTest(Parent)'
        if not isinstance(parent, ast.Name):
            # 'class FooTest(bar.Bar)' not supported within
            # a module
            continue
        parent_class = parent.id

        # From this point we use `_$variable` to name temporary returns
        # from method calls that are to-be-assigned/combined with the
        # existing `$variable`.
        _info, _disable, _match = _examine_class(target_module,
                                                 target_class,
                                                 determine_match,
                                                 module.path,
                                                 parent_class,
                                                 match)
        if _info:
            parents.remove(parent)
            _extend_test_list(info, _info)
            disabled.update(_disable)
        if _match is not match:
            match = _match

    return match


class ClassNotSuitable(Exception):
    """Exception raised when examination of a class should not proceed."""


def _get_attributes_for_further_examination(parent, module):
    """Returns path, module and class for further examination.

    This looks at one of the parents of an interesting class, so for the
    example class Test below:

    >>> class Test(unittest.TestCase, MixIn):
    >>>   pass

    This function should be called twice: once for unittest.TestCase,
    and once for MixIn.

    :param parent: parent is one of the possibly many parents from
                   which the class being examined inherits from.
    :type parent: :class:`ast.Attribute`
    :param module: PythonModule instance with information about the
                   module being inspected
    :type module: :class:`avocado.core.safeloader.module.PythonModule`
    :raises: ClassNotSuitable
    :returns: a tuple with three values: the class name, the imported
              symbol instance matching the further examination step,
              and a hint about the symbol name also being a module.
    :rtype: tuple of (str,
            :class:`avocado.core.safeloader.imported.ImportedSymbol`,
            bool)
    """
    if hasattr(parent, 'value'):
        # A "value" in an "attribute" in this context means that
        # there's a "module.class" notation.  It may be called that
        # way, because it resembles "class" being an attribute of the
        # "module" object.  In short, if "parent" has a "value"
        # attribute, it means that this is given as a
        # "module.parent_class" notation, meaning that:
        # - parent is a module
        # - parent.value *should* be a class, because there's
        #   currently no support for the "module.module.parent_class"
        #   notation.  See issue #4706.
        klass = parent.value
        if not hasattr(klass, 'id'):
            # We don't support multi-level 'parent.parent.Class'
            raise ClassNotSuitable
        else:
            # We know 'parent.Class' or 'asparent.Class' and need
            # to get path and original_module_name. Class is given
            # by parent definition.
            imported_symbol = module.imported_symbols.get(klass.id)
            if imported_symbol is None:
                # We can't examine this parent (probably broken module)
                raise ClassNotSuitable

            # We currently don't support classes whose parents are generics
            if isinstance(parent, ast.Subscript):
                raise ClassNotSuitable

            parent_class = parent.attr

            # Special situation: in this case, because we know the parent
            # class is given as, module.class notation, we know what the
            # module name is.  The imported symbol, because of its knowledge
            # *only* about the imports, and not about the class definitions,
            # can not tell if an import is a "from module import other_module"
            # or a "from module import class"
            symbol_is_module = (klass.id == imported_symbol.symbol_name)

    else:
        # We only know 'Class' or 'AsClass' and need to get
        # path, module and original class_name
        klass = parent.id
        imported_symbol = module.imported_symbols.get(klass)
        if imported_symbol is None:
            # We can't examine this parent (probably broken module)
            raise ClassNotSuitable

        parent_class = imported_symbol.symbol
        symbol_is_module = False

    return parent_class, imported_symbol, symbol_is_module


def _find_import_match(parent_path, parent_module):
    """Attempts to find an importable module."""
    modules_paths = [parent_path] + sys.path
    found_spec = PathFinder.find_spec(parent_module, modules_paths)
    if found_spec is None:
        raise ClassNotSuitable
    return found_spec


def _examine_class(target_module, target_class, determine_match, path,
                   class_name, match):
    """
    Examine a class from a given path

    :param target_module: the name of the module from which a class should
                          have come from.  When attempting to find a Python
                          unittest, the target_module will most probably
                          be "unittest", as per the standard library module
                          name.  When attempting to find Avocado tests, the
                          target_module will most probably be "avocado".
    :type target_module: str
    :param target_class: the name of the class that is considered to contain
                         test methods.  When attempting to find Python
                         unittests, the target_class will most probably be
                         "TestCase".  When attempting to find Avocado tests,
                         the target_class  will most probably be "Test".
    :type target_class: str
    :param determine_match: a callable that will determine if a match has
                            occurred or not
    :type determine_match: function
    :param path: path to a Python source code file
    :type path: str
    :param class_name: the specific class to be found
    :type path: str
    :param match: whether the inheritance from <target_module.target_class> has
                  been determined or not
    :type match: bool
    :returns: tuple where first item is a list of test methods detected
              for given class; second item is set of class names which
              look like avocado tests but are force-disabled.
    :rtype: tuple
    """
    module = PythonModule(path, target_module, target_class)
    info = []
    disabled = set()

    for klass in module.iter_classes(class_name):
        if class_name != klass.name:
            continue

        docstring = ast.get_docstring(klass)

        if match is False:
            match = module.is_matching_klass(klass)

        info = get_methods_info(klass.body,
                                get_docstring_directives_tags(docstring),
                                get_docstring_directives_dependencies(
                                    docstring))

        # Getting the list of parents of the current class
        parents = klass.bases

        match = _examine_same_module(parents, info, disabled, match, module,
                                     target_module, target_class, determine_match)

        # If there are parents left to be discovered, they
        # might be in a different module.
        for parent in parents:
            try:
                (parent_class,
                 imported_symbol,
                 symbol_is_module) = _get_attributes_for_further_examination(parent,
                                                                             module)

                found_spec = imported_symbol.get_importable_spec(symbol_is_module)
                if found_spec is None:
                    continue

            except ClassNotSuitable:
                continue

            _info, _disabled, _match = _examine_class(target_module,
                                                      target_class,
                                                      determine_match,
                                                      found_spec.origin,
                                                      parent_class,
                                                      match)
            if _info:
                _extend_test_list(info, _info)
                disabled.update(_disabled)
            if _match is not match:
                match = _match

    if not match and module.interesting_klass_found:
        imported_symbol = module.imported_symbols[class_name]
        if imported_symbol:
            found_spec = imported_symbol.get_importable_spec()
            if found_spec:
                _info, _disabled, _match = _examine_class(target_module,
                                                          target_class,
                                                          determine_match,
                                                          found_spec.origin,
                                                          class_name,
                                                          match)
                if _info:
                    _extend_test_list(info, _info)
                    disabled.update(_disabled)
                if _match is not match:
                    match = _match

    return info, disabled, match


def find_python_tests(target_module, target_class, determine_match, path):
    """
    Attempts to find Python tests from source files

    A Python test in this context is a method within a specific type
    of class (or that inherits from a specific class).

    :param target_module: the name of the module from which a class should
                          have come from.  When attempting to find a Python
                          unittest, the target_module will most probably
                          be "unittest", as per the standard library module
                          name.  When attempting to find Avocado tests, the
                          target_module will most probably be "avocado".
    :type target_module: str
    :param target_class: the name of the class that is considered to contain
                         test methods.  When attempting to find Python
                         unittests, the target_class will most probably be
                         "TestCase".  When attempting to find Avocado tests,
                         the target_class  will most probably be "Test".
    :type target_class: str
    :type determine_match: a callable that will determine if a given module
                           and class is contains valid Python tests
    :type determine_match: function
    :param path: path to a Python source code file
    :type path: str
    :returns: tuple where first item is dict with class name and additional
              info such as method names and tags; the second item is
              set of class names which look like Python tests but have been
              forcefully disabled.
    :rtype: tuple
    """
    module = PythonModule(path, target_module, target_class)
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
                                    get_docstring_directives_dependencies(
                                        docstring))
            result[klass.name] = info
            continue

        # From this point onwards we want to do recursive discovery, but
        # for now we don't know whether it is avocado.Test inherited
        # (Ifs are optimized for readability, not speed)

        # If "recursive" tag is specified, it is forced as test
        if check_docstring_directive(docstring, 'recursive'):
            match = True
        else:
            match = module.is_matching_klass(klass)
        info = get_methods_info(klass.body,
                                get_docstring_directives_tags(docstring),
                                get_docstring_directives_dependencies(
                                    docstring))
        # Getting the list of parents of the current class
        parents = klass.bases

        match = _examine_same_module(parents, info, disabled, match, module,
                                     target_module, target_class, determine_match)

        # If there are parents left to be discovered, they
        # might be in a different module.
        for parent in parents:
            try:
                (parent_class,
                 imported_symbol,
                 symbol_is_module) = _get_attributes_for_further_examination(parent,
                                                                             module)

                found_spec = imported_symbol.get_importable_spec(symbol_is_module)
                if found_spec is None:
                    continue

            except ClassNotSuitable:
                continue

            _info, _dis, _match = _examine_class(target_module,
                                                 target_class,
                                                 determine_match,
                                                 found_spec.origin,
                                                 parent_class,
                                                 match)
            if _info:
                info.extend(_info)
                disabled.update(_dis)
            if _match is not match:
                match = _match

        # Only update the results if this was detected as 'avocado.Test'
        if match:
            result[klass.name] = info

    return result, disabled


def _determine_match_python(module, klass, docstring):
    """
    Implements the match check for all Python based test classes

    Meaning that the enable/disabled/recursive tags are respected for
    Avocado Instrumented Tests and Python unittests.
    """
    directives = get_docstring_directives(docstring)
    if 'disable' in directives:
        return False
    if 'enable' in directives:
        return True
    if 'recursive' in directives:
        return True
    # Still not decided, try inheritance
    return module.is_matching_klass(klass)


def find_avocado_tests(path):
    return find_python_tests('avocado', 'Test', _determine_match_python, path)


def find_python_unittests(path):
    found, _ = find_python_tests('unittest', 'TestCase',
                                 _determine_match_python, path)
    return found
