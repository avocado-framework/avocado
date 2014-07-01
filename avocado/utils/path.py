import os


def get_path(base_path, user_path):
    """
    Translate a user specified path to a real path.

    If user_path is relative, append it to base_path.
    If user_path is absolute, return it as is.

    :param base_path: The base path of relative user specified paths.
    :param user_path: The user specified path.
    """
    if os.path.isabs(user_path):
        return user_path
    else:
        return os.path.join(base_path, user_path)


def get_relative_path(path, reference):
    """
    Given 2 absolute paths "path" and "reference", compute the path of
    "path" as relative to the directory "reference".

    :param path: The absolute path to convert to a relative path.
    :param reference: An absolute directory path to which the relative
                      path will be computed.
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
