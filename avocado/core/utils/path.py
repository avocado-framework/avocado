import os

from pkg_resources import get_distribution


def prepend_base_path(value):
    expanded = os.path.expanduser(value)
    if not expanded.startswith(('/', '~', '.')):
        dist = get_distribution('avocado-framework')
        return os.path.join(dist.location, 'avocado', expanded)
    return expanded


def system_wide_or_base_path(file_path):
    """Returns either a system wide path, or one relative to the base.

    If "etc/avocado/avocado.conf" is given as input, it checks for the
    existence of "/etc/avocado/avocado.conf".  If that path does not exist,
    then a path starting with the avocado's Python's distribution is returned.
    In that case it'd return something like
    "/usr/lib/python3.9/site-packages/avocado/etc/avocado/avocado.conf".

    :param file_path: a filesystem path that can either be absolute, or
                      relative.  If relative, the absolute equivalent
                      (that is, by prefixing the filesystem root location)
                      is checked for existence.  If it does not exist, a
                      path relative to the Python's distribution base path
                      is returned.
    :type file_path: str
    :rtype: str
    """
    if os.path.isabs(file_path):
        abs_path = file_path
    else:
        abs_path = os.path.join(os.path.sep, file_path)
    if os.path.exists(abs_path):
        return abs_path
    return prepend_base_path(file_path)
