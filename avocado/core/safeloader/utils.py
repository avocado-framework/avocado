import collections


def get_statement_import_as(statement):
    """
    Returns a mapping of imported module names whether using aliases or not

    :param statement: an AST import statement
    :type statement: ast.Import
    :returns: a mapping of names {<realname>: <alias>} of modules imported
    :rtype: collections.OrderedDict
    """
    result = collections.OrderedDict()
    for name in statement.names:
        if name.asname is not None:
            result[name.name] = name.asname
        else:
            result[name.name] = name.name
    return result
