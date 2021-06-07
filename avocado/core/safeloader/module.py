import ast
import os


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

    @staticmethod
    def _get_adjusted_path_for_level(statement, path):
        level = getattr(statement, 'level', 0)
        if level is None:
            level = 0
        for _ in range(level - 1):
            path = os.path.dirname(path)
        return path

    def _get_imported_path_from_statement(self, statement):
        """Returns the imported path, from absolute or relative import."""
        abs_path_of_module_dir = os.path.abspath(os.path.dirname(self.path))
        imported_path = self._get_adjusted_path_for_level(statement,
                                                          abs_path_of_module_dir)
        if getattr(statement, 'module', None) is not None:
            # Module has a name, so its path is absolute, and not relative
            # to the directory structure
            module_path = statement.module.replace('.', os.path.sep)
            imported_path = os.path.join(imported_path, module_path)
        return imported_path

    def add_imported_object(self, statement):
        """
        Keeps track of objects names and importable entities
        """
        imported_path = self._get_imported_path_from_statement(statement)
        for name in statement.names:
            full_path = os.path.join(imported_path,
                                     name.name.replace('.', os.path.sep))
            final_name = self._get_name_from_alias_statement(name)
            self.imported_objects[final_name] = full_path

    @staticmethod
    def _get_name_from_alias_statement(alias):
        """Returns the aliased name or original one."""
        return alias.asname if alias.asname else alias.name

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
