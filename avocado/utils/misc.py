# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; specifically version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# This code was inspired in the autotest project,
# client/shared/utils.py
# Authors: Martin J Bligh <mbligh@google.com>, Andy Whitcroft <apw@shadowen.org>

import re
import time

import logging

log = logging.getLogger('avocado.test')


def unique(lst):
    """
    Return a list of the elements in list, but without duplicates.

    :param lst: List with values.
    :return: List with non duplicate elements.
    """
    return list(set(lst))


def convert_data_size(size, default_sufix='B'):
    '''
    Convert data size from human readable units to an int of arbitrary size.

    :param size: Human readable data size representation (string).
    :param default_sufix: Default sufix used to represent data.
    :return: Int with data size in the appropriate order of magnitude.
    '''
    orders = {'B': 1,
              'K': 1024,
              'M': 1024 * 1024,
              'G': 1024 * 1024 * 1024,
              'T': 1024 * 1024 * 1024 * 1024,
              }

    order = re.findall("([BbKkMmGgTt])", size[-1])
    if not order:
        size += default_sufix
        order = [default_sufix]

    return int(float(size[0:-1]) * orders[order[0].upper()])


def normalize_data_size(value_str, order_magnitude="M", factor="1024"):
    """
    Normalize a data size in one order of magnitude to another (MB to GB,
    for example).

    :param value_str: a string include the data and unit
    :param order_magnitude: the magnitude order of result
    :param factor: the factor between two relative order of magnitude.
                   Normally could be 1024 or 1000
    """
    def _get_magnitude_index(magnitude_list, magnitude_value):
        for i in magnitude_list:
            order_magnitude = re.findall("[\s\d](%s)" % i,
                                         str(magnitude_value), re.I)
            if order_magnitude:
                return magnitude_list.index(order_magnitude[0].upper())
        return -1

    magnitude_list = ['B', 'K', 'M', 'G', 'T']
    try:
        data = float(re.findall("[\d\.]+", value_str)[0])
    except IndexError:
        logging.error("Incorrect data size format. Please check %s"
                      " has both data and unit." % value_str)
        return ""

    magnitude_index = _get_magnitude_index(magnitude_list, value_str)
    order_magnitude_index = _get_magnitude_index(magnitude_list,
                                                 " %s" % order_magnitude)

    if data == 0:
        return 0
    elif magnitude_index < 0 or order_magnitude_index < 0:
        logging.error("Unknown input order of magnitude. Please check your"
                      "value '%s' and desired order of magnitude"
                      " '%s'." % (value_str, order_magnitude))
        return ""

    if magnitude_index > order_magnitude_index:
        multiple = float(factor)
    else:
        multiple = float(factor) ** -1

    for _ in range(abs(magnitude_index - order_magnitude_index)):
        data *= multiple

    return str(data)


def wait_for(func, timeout, first=0.0, step=1.0, text=None):
    """
    Wait until func() evaluates to True.

    If func() evaluates to True before timeout expires, return the
    value of func(). Otherwise return None.

    :param timeout: Timeout in seconds
    :param first: Time to sleep before first attempt
    :param steps: Time to sleep between attempts in seconds
    :param text: Text to print while waiting, for debug purposes
    """
    start_time = time.time()
    end_time = time.time() + timeout

    time.sleep(first)

    while time.time() < end_time:
        if text:
            log.debug("%s (%f secs)", text, (time.time() - start_time))

        output = func()
        if output:
            return output

        time.sleep(step)

    return None
