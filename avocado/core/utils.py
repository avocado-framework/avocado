import os

from pkg_resources import get_distribution


def prepend_base_path(value):
    expanded = os.path.expanduser(value)
    if not expanded.startswith(('/', '~', '.')):
        dist = get_distribution('avocado-framework')
        return os.path.join(dist.location, 'avocado', expanded)
    return expanded
