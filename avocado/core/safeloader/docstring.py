import json
import re

#: Gets the docstring directive value from a string. Used to tweak
#: test behavior in various ways
DOCSTRING_DIRECTIVE_RE_RAW = r'\s*:avocado:[ \t]+(([a-zA-Z0-9]+?[a-zA-Z0-9_:,\=\-\.]*)|(requirement={.*}))\s*$'
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
