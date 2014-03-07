import logging
import os

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


def write_one_line(filename, line):
    write_file(filename, line.rstrip('\n') + '\n')


def write_file(filename, data):
    with open(filename, 'w') as file_obj:
        file_obj.write(data)


def get_relative_path(path, reference):
    """
    Given 2 absolute paths "path" and "reference", compute the path of
    "path" as relative to the directory "reference".

    :param path the absolute path to convert to a relative path
    :param reference an absolute directory path to which the relative
        path will be computed
    """
    # normalize the paths (remove double slashes, etc)
    assert(os.path.isabs(path))
    assert(os.path.isabs(reference))

    path = os.path.normpath(path)
    reference = os.path.normpath(reference)

    # we could use os.path.split() but it splits from the end
    path_list = path.split(os.path.sep)[1:]
    ref_list = reference.split(os.path.sep)[1:]

    # find the longest leading common path
    for i in xrange(min(len(path_list), len(ref_list))):
        if path_list[i] != ref_list[i]:
            # decrement i so when exiting this loop either by no match or by
            # end of range we are one step behind
            i -= 1
            break
    i += 1
    # drop the common part of the paths, not interested in that anymore
    del path_list[:i]

    # for each uncommon component in the reference prepend a ".."
    path_list[:0] = ['..'] * (len(ref_list) - i)

    return os.path.join(*path_list)


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
