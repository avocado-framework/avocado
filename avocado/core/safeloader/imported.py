import ast
import os
import sys
from importlib.machinery import PathFinder

from avocado.core.safeloader.utils import get_statement_import_as


class ImportedSymbol:
    """A representation of an importable symbol.

    Attributes:

    module_path : str
    symbol : str
    importer_fs_path: str or None
    """

    def __init__(self, module_path, symbol='', importer_fs_path=None,
                 module_alias='', symbol_alias=''):
        #: Path from where the symbol was imported.  On a statement such as
        #: "import os", module_path is "os" and there's no symbol.
        #: On a statement such as from unittest.mock import mock_open",
        #: the module_path is "unittest.mock".  On a statement such as
        #: "from ..foo import bar", module_path is "..foo" (relative).
        self.module_path = module_path
        #: The name of the imported symbol.  On a statement such as
        #: "import os", there's no symbol.  On a statement such as
        #: "from unittest import mock"", the symbol is "mock" (even
        #: though it may actually also be a module, but it's impossible
        #: to know for sure).  On a statement such as "from unittest.mock
        #: import mock_open", symbol is "mock_open".
        self.symbol = symbol
        #: The full, absolute filesystem path of the module importing
        #: this symbol.  This is used for relative path calculations,
        #: but it's limited to relative modules that also share the
        #: filesystem location.  An example is "/path/to/mytest.py",
        #: that can contain:
        #:
        #: from .base import BaseTestClass
        #:
        #: And thus will have a symbol of "BaseTestClass" and the
        #: module as ".base".  The relative filesystem path of the
        #: module (which should contain the symbol) will be
        #: "/path/to".
        #:
        #: And if "/path/to/common/test.py" contains:
        #:
        #: from ..base import BaseTestClass
        #:
        #: The relative filesystem path of the module (which should
        #: contain the symbol) will be "/path/to".
        self.importer_fs_path = importer_fs_path
        #: An optional alias for the module, such as when a
        #: "import os as operating_system" statement is given.
        self.module_alias = module_alias
        #: An optional alias the symbol, such as when a
        #: "from os import path as os_path" is given
        self.symbol_alias = symbol_alias

    def _walk_importable_components(self, symbol_is_module=False):
        if symbol_is_module:
            full_name = f"{self.module_path}.{self.symbol}"
        else:
            full_name = self.module_path
        # Stripping leading dots, as relative paths will be handled with
        # insertion to module_paths with the relative path
        components = full_name.strip(".").split(".")
        for index, component in enumerate(components):
            if index > 0:
                previous = components[index - 1]
            else:
                previous = ''
            yield (component, previous)

    def get_importable_spec(self, symbol_is_module=False):
        """Returns the specification of an actual importable module.

        This is a check based on the limitations that we do not
        actually perform an import, and assumes a directory structure
        with modules.

        :param symbol_is_module: if it's known that the symbol is also
                                 a module, include it in the search for
                                 an importable spec
        :type symbol_is_module: bool
        """
        modules_paths = sys.path
        modules_paths.insert(0, self.get_relative_module_fs_path())
        spec = None
        for component, previous in self._walk_importable_components(symbol_is_module):
            if previous:
                modules_paths = [os.path.join(mod, previous) for
                                 mod in modules_paths[:]]
            spec = PathFinder.find_spec(component, modules_paths)
            if spec is None:
                break
        return spec

    def is_importable(self, symbol_is_module=False):
        """Checks whether this imported symbol seems to be importable.

        This is a check based on the limitations that we do not
        actually perform an import, and assumes a directory structure
        with modules.

        :param symbol_is_module: if it's known that the symbol is also
                                 a module, include it in the search for
                                 an importable spec
        :type symbol_is_module: bool
        """
        return self.get_importable_spec(symbol_is_module) is not None

    @staticmethod
    def _split_last_module_path_component(module_path):
        """Splits a module path into a lower and topmost components.

        It also discards any information about relative location.

        :param module_path: a module path, such as "os" or "os.path"
                            or "..selftests.utils"
        :type module_path: str
        :returns: the lower and topmost components
        :rtype: tuple
        """
        non_relative = module_path.strip('.')
        if '.' in non_relative:
            module_components = non_relative.rsplit('.', 1)
            if len(module_components) == 2:
                return (module_components[0], module_components[1])
        return ('', non_relative)

    @staticmethod
    def _get_relative_prefix(statement):
        """Returns the string that represents to the relative import level.

        :param statement: an "import from" ast statement
        :type statement: :class:`ast.ImportFrom`
        :returns: the string that represents the relative import level.
        :rtype: str
        """
        relative_level = getattr(statement, 'level', 0) or 0
        return ''.join(['.' for _ in range(relative_level)])

    @staticmethod
    def get_symbol_from_statement(statement):
        return ImportedSymbol.get_symbol_module_path_from_statement(statement)[0]

    @staticmethod
    def get_module_path_from_statement(statement):
        return ImportedSymbol.get_symbol_module_path_from_statement(statement)[1]

    @staticmethod
    def get_symbol_module_path_from_statement(statement, name_index=0):
        symbol = ''
        module_path = ''
        module_alias = ''
        symbol_alias = ''
        import_as = get_statement_import_as(statement)
        names = list(import_as.keys())
        as_names = list(import_as.values())

        if isinstance(statement, ast.Import):
            # On an Import statement, it's impossible to import a symbol
            # so everything is the module_path
            module_path = names[name_index]
            module_alias = as_names[name_index]

        elif isinstance(statement, ast.ImportFrom):
            symbol = names[name_index]
            relative = ImportedSymbol._get_relative_prefix(statement)
            module_name = statement.module or ''
            module_path = relative + module_name
            symbol_alias = as_names[name_index]

        return symbol, module_path, module_alias, symbol_alias

    @property
    def module_name(self):
        """The final name of the module from its importer perspective.

        If a alias exists, it will be the alias name.  If not, it will
        be the original name.
        """
        if self.module_alias:
            return self.module_alias
        return self.module_path

    @property
    def symbol_name(self):
        """The final name of the symbol from its importer perspective.

        If a alias exists, it will be the alias name.  If not, it will
        be the original name.
        """
        if self.symbol_alias:
            return self.symbol_alias
        return self.symbol

    @classmethod
    def from_statement(cls, statement, importer_fs_path=None, index=0):
        (symbol,
         module_path,
         module_alias,
         symbol_alias) = cls.get_symbol_module_path_from_statement(statement, index)
        return cls(module_path, symbol, importer_fs_path, module_alias, symbol_alias)

    def to_str(self):
        """Returns a string representation of the plausible statement used."""
        if not self.symbol:
            return f"import {self.module_path}"
        return f"from {self.module_path} import {self.symbol}"

    def is_relative(self):
        """Returns whether the imported symbol is on a relative path."""
        return self.module_path.startswith(".")

    def get_relative_module_fs_path(self):
        """Returns the module base dir, based on its relative path

        The base dir for the module is the directory where one is
        expected to find the first module of the module path.  For a
        module path of "..foo.bar", and its importer being at
        "/abs/path/test.py", the base dir where "foo" is supposed to
        be found would be "/abs".  And as a consequence, "bar" would
        be found at "/abs/foo/bar".

        This assumes that the module path is indeed related to the location
        of its importer.  This may not be true if the namespaces match, but
        are distributed across different filesystem paths.
        """
        path = os.path.dirname(self.importer_fs_path)
        for char in self.module_path[1:]:
            if char != ".":
                break
            path = os.path.dirname(path)
        return path

    def get_parent_fs_path(self):
        if self.is_relative():
            return self.get_relative_module_fs_path()
        parent_path = os.path.dirname(self.importer_fs_path)
        if self.module_path:
            return os.path.join(parent_path, self.module_path)
        return parent_path

    def __repr__(self):
        return (f'<ImportedSymbol module_path="{self.module_path}"'
                f'symbol="{self.symbol}"'
                f'importer_fs_path="{self.importer_fs_path}">')

    def __eq__(self, other):
        return ((self.module_path == other.module_path) and
                (self.symbol == other.symbol) and
                (self.importer_fs_path == other.importer_fs_path))
