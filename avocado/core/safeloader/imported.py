import ast
import os

from .utils import get_statement_import_as


class ImportedSymbol:
    """A representation of an importable symbol.

    Attributes:

    symbol : str
    module_path : str
    importer_fs_path: str or None
    """

    def __init__(self, symbol, module_path='', importer_fs_path=None):
        #: The name of the imported symbol.  On a statement such as
        #: "import os", the symbol is "os".  On a statement such as
        #: "from unittest.mock import mock_open", the symbol is "mock_open"
        self.symbol = symbol
        #: Path from where the symbol was imported.  On a statement such as
        #: "import os", module_path is None.  On a statement such as
        #: "from unittest.mock import mock_open", the module_path is
        #: "unittest.mock".  On a statement such as "from ..foo import bar",
        #: module_path is "..foo" (relative).
        self.module_path = module_path
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
        names = list(get_statement_import_as(statement).keys())

        if isinstance(statement, ast.Import):
            module_path = names[name_index]
            module_path, symbol = ImportedSymbol._split_last_module_path_component(module_path)
            return symbol, module_path

        elif isinstance(statement, ast.ImportFrom):
            symbol = names[name_index]
            relative = ImportedSymbol._get_relative_prefix(statement)
            module_name = statement.module or ''
            module_path = relative + module_name

        return symbol, module_path

    @classmethod
    def from_statement(cls, statement, importer_fs_path=None):
        symbol, module_path = cls.get_symbol_module_path_from_statement(statement)
        return cls(symbol, module_path, importer_fs_path)

    def to_str(self):
        """Returns a string representation of the plausible statement used."""
        if not self.module_path:
            return "import %s" % self.symbol
        return "from %s import %s" % (self.module_path, self.symbol)

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

    def get_compat_parent_path(self):
        """Returns a "parent path" compatible with the path based notation.

        This is intended for temporary compatibility purposes with the
        single path based notation of keeping track of the path/module/class.
        """
        parent_path = self.get_relative_module_fs_path()
        non_rel_mod_path = self.module_path.strip(".")
        pure_module_path_to_fs = non_rel_mod_path.replace(".", os.path.sep)
        if self.symbol:
            pure_module_path_to_fs = os.path.dirname(pure_module_path_to_fs)
        return os.path.join(parent_path, pure_module_path_to_fs)

    def get_compat_module_path(self):
        """Returns a "parent module" compatible with the path based notation.

        This is intended for temporary compatibility purposes with the
        single path based notation of keeping track of the path/module/class.
        """
        non_rel_mod_path = self.module_path.strip(".")
        split = non_rel_mod_path.rsplit(".", 1)
        if len(split) > 1:
            return split[1]
        return non_rel_mod_path

    def get_compat_symbol(self):
        """Returns a "parent symbol" compatible with the path based notation.

        This is intended for temporary compatibility purposes with the
        single path based notation of keeping track of the path/module/class.
        """
        split = self.symbol.rsplit(".", 1)
        if len(split) > 1:
            return split[1]
        return self.symbol

    def __repr__(self):
        return ('<ImportedSymbol symbol="%s" module_path="%s" '
                'importer_fs_path="%s">' % (self.symbol,
                                            self.module_path,
                                            self.importer_fs_path))

    def __eq__(self, other):
        return ((self.symbol == other.symbol) and
                (self.module_path == other.module_path) and
                (self.importer_fs_path == other.importer_fs_path))
