import ast
import collections


def get_statement_import_as(statement):
    """
    Returns a mapping of imported module names whether using aliases or not

    :param statement: an AST import statement
    :type statement: ast.Import
    :returns: a mapping of names {<realname>: <alias>} of modules imported
    :rtype: collections.OrderedDict
    """
    if not any([isinstance(statement, ast.Import),
                isinstance(statement, ast.ImportFrom)]):
        raise ValueError("Value given is not an ast import or "
                         "import from statement")
    result = collections.OrderedDict()
    for name in statement.names:
        if name.asname is not None:
            result[name.name] = name.asname
        else:
            result[name.name] = name.name
    return result
