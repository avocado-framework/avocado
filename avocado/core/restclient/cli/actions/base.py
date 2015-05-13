# Copyright: Red Hat Inc. 2015
# Author: Cleber Rosa <cleber@redhat.com>


def action(function):
    """
    Simple function that marks functions as CLI actions

    :param function: the function that will receive the CLI action mark
    """
    function.is_action = True
    return function
