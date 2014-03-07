import logging

log = logging.getLogger('avocado.utils')

def ask(question, auto=False):
    """
    Raw input with a prompt.

    :param question: Question to be asked
    :param auto: Whether to return "y" instead of asking the question
    """
    if auto:
        log.info("%s (y/n) y" % question)
        return "y"
    return raw_input("%s (y/n) " % question)


def read_file(filename):
    """
    Read the entire contents of file.
    """
    with open(filename, 'r') as file_obj:
        contents = file_obj.read()
    return contents

    f = open(filename)
    try:
        return f.read()
    finally:
        f.close()


def read_one_line(filename):
    """
    Read the first line of filename.
    """
    with open(filename, 'r') as file_obj:
        line = file_obj.readline().rstrip('\n')
    return line


def unique(lst):
    """
    Return a list of the elements in list, but without duplicates.

    :param lst: List with values.
    :return: List with non duplicate elements.
    """
    n = len(lst)
    if n == 0:
        return []
    u = {}
    try:
        for x in lst:
            u[x] = 1
    except TypeError:
        return None
    else:
        return u.keys()
