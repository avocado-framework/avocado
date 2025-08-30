# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: Red Hat Inc. 2014
#            IBM, 2023
#
# Authors: Ruda Moura <rmoura@redhat.com>
#          Lucas Meneghel Rodrigues <lmr@redhat.com>
#          Harish S <harisrir@linux.vnet.ibm.com>
#          Maram Srimannarayana Murthy <Maram.Srimannarayana.Murthy@ibm.com>
#

"""This module contains handy classes that can be used inside
avocado core code or plugins.
"""


import math
import re
import sys


class InvalidDataSize(ValueError):
    """Signals that the value given to :class:`DataSize` is not valid.

    This exception is raised when an invalid data size string is provided
    to the DataSize class constructor.
    """


def ordered_list_unique(object_list):
    """Returns an unique list of objects, with their original order preserved.

    This function removes duplicates from a list while maintaining the
    original order of the first occurrence of each element.

    :param object_list: List of objects that may contain duplicates
    :type object_list: list
    :returns: List with duplicates removed, order preserved
    :rtype: list

    Example::

        >>> ordered_list_unique([1, 2, 2, 3, 1, 4])
        [1, 2, 3, 4]
    """
    seen = set()
    seen_add = seen.add
    return [x for x in object_list if not (x in seen or seen_add(x))]


def geometric_mean(values):
    """Evaluates the geometric mean for a list of numeric values.

    This implementation is slower but allows unlimited number of values.
    The geometric mean is calculated as the nth root of the product of n numbers.

    :param values: List with numeric values
    :type values: list
    :returns: Single value representing the geometric mean for the list values,
              or None if the list is empty
    :rtype: float or None
    :raises ValueError: If any value in the list cannot be converted to int

    :see: http://en.wikipedia.org/wiki/Geometric_mean

    Example::

        >>> geometric_mean([1, 2, 4, 8])
        2.8284271247461903
    """
    try:
        values = [int(value) for value in values]
    except ValueError as exc:
        raise ValueError(f"Invalid inputs {values}. Provide valid inputs") from exc
    no_values = len(values)
    if not no_values:
        return None
    return math.exp(sum(math.log(number) for number in values) / no_values)


def compare_matrices(matrix1, matrix2, threshold=0.05):  # pylint: disable=R0912
    """Compare 2 matrices nxm and return a matrix nxm with comparison data and stats.

    When the first columns match, they are considered as header and
    included in the results intact. This function is useful for comparing
    performance data between different test runs.

    :param matrix1: Reference Matrix of floats; first column could be header
    :type matrix1: list of lists
    :param matrix2: Matrix that will be compared; first column could be header
    :type matrix2: list of lists
    :param threshold: Any difference greater than this percent threshold will
                      be reported (default: 0.05 = 5%)
    :type threshold: float
    :returns: Tuple containing:
              - Matrix with the difference in comparison
              - Number of improvements
              - Number of regressions
              - Total number of comparisons
    :rtype: tuple(list, int, int, int)

    Example::

        >>> matrix1 = [['test1', 10.0, 20.0]]
        >>> matrix2 = [['test1', 12.0, 18.0]]
        >>> result = compare_matrices(matrix1, matrix2)
        >>> # Returns comparison matrix and statistics
    """
    improvements = 0
    regressions = 0
    same = 0
    new_matrix = []

    for line1, line2 in zip(matrix1, matrix2):
        new_line = []
        elements = iter(zip(line1, line2))
        try:
            element1, element2 = next(elements)
        except StopIteration:  # no data in this row
            new_matrix.append(new_line)
            continue
        if element1 == element2:  # this column contains header
            new_line.append(element1)
            try:
                element1, element2 = next(elements)
            except StopIteration:
                new_matrix.append(new_line)
                continue
        while True:
            try:
                ratio = float(element2) / float(element1)
            except ZeroDivisionError:  # For 0s, allow exact match or error
                if not float(element2):
                    new_line.append(".")
                    same += 1
                else:
                    new_line.append(f"error_{element2}/{element1}")
                    improvements += 1
                try:
                    element1, element2 = next(elements)
                except StopIteration:
                    break
                continue
            if ratio < (1 - threshold):  # handling regression
                regressions += 1
                new_line.append(100 * ratio - 100)
            elif ratio > (1 + threshold):  # handling improvements
                improvements += 1
                new_line.append(f"+{100 * ratio - 100:.6g}")
            else:
                same += 1
                new_line.append(".")
            try:
                element1, element2 = next(elements)
            except StopIteration:
                break
        new_matrix.append(new_line)

    total = improvements + regressions + same
    return (new_matrix, improvements, regressions, total)


def comma_separated_ranges_to_list(string):
    """Provides a list from comma separated ranges.

    Converts a string containing comma-separated ranges into a list of integers.
    Ranges can be specified as single numbers or as ranges using hyphens.

    :param string: String of comma separated range (e.g., "1,3-5,7")
    :type string: str
    :returns: List of integer values in comma separated range
    :rtype: list of int
    :raises ValueError: If the string contains invalid range format

    Example::

        >>> comma_separated_ranges_to_list("1,3-5,7")
        [1, 3, 4, 5, 7]
        >>> comma_separated_ranges_to_list("10-12")
        [10, 11, 12]
    """
    values = []
    for range_str in string.split(","):
        if "-" in range_str:
            start, end = range_str.split("-")
            values.extend(range(int(start), int(end) + 1))
        else:
            values.append(int(range_str))
    return values


def recursive_compare_dict(dict1, dict2, level="DictKey", diff_btw_dict=None):
    """Finds difference between two dictionaries.

    Recursively compares two dictionaries and returns a list of differences.
    The function handles nested structures and provides detailed difference information.

    :param dict1: First dictionary to compare
    :type dict1: dict, list, or any
    :param dict2: Second dictionary to compare
    :type dict2: dict, list, or any
    :param level: Current level identifier for nested comparison
    :type level: str
    :param diff_btw_dict: List to store differences (used internally for recursion)
    :type diff_btw_dict: list or None
    :returns: List of differences between the two dictionaries, or None for recursive calls
    :rtype: list or None

    Example::

        >>> dict1 = {'a': 1, 'b': {'c': 2}}
        >>> dict2 = {'a': 2, 'b': {'c': 2}}
        >>> differences = recursive_compare_dict(dict1, dict2)
        >>> # Returns list of differences
    """
    if diff_btw_dict is None:
        diff_btw_dict = []
    if isinstance(dict1, dict) and isinstance(dict2, dict):
        if dict1.keys() != dict2.keys():
            set1 = set(dict1.keys())
            set2 = set(dict2.keys())
            diff_btw_dict.append(f"{level} + {set1-set2} - {set2-set1}")
            common_keys = set1 & set2
        else:
            common_keys = set(dict1.keys())
        for k in common_keys:
            recursive_compare_dict(
                dict1[k], dict2[k], level=f"{level}.{k}", diff_btw_dict=diff_btw_dict
            )
        return diff_btw_dict
    if isinstance(dict1, list) and isinstance(dict2, list):
        if len(dict1) != len(dict2):
            diff_btw_dict.append(f"{level} + {len(dict1)} - {len(dict2)}")
        common_len = min(len(dict1), len(dict2))
        for i in range(common_len):
            recursive_compare_dict(
                dict1[i],
                dict2[i],
                level=f"{level}.{dict1[i]}",
                diff_btw_dict=diff_btw_dict,
            )
    else:
        if dict1 != dict2:
            diff_btw_dict.append(f"{level} - dict1 value:{dict1}, dict2 value:{dict2}")
    return None


class Borg:
    """Multiple instances of this class will share the same state.

    This is considered a better design pattern in Python than
    more popular patterns, such as the Singleton. The Borg pattern
    allows multiple instances to exist but they all share the same
    state, making them effectively equivalent. Inspired by
    Alex Martelli's article mentioned below.

    All instances of this class will have the same ``__dict__``,
    so any changes to instance variables will be reflected across
    all instances.

    :see: http://www.aleax.it/5ep.html

    Example::

        >>> b1 = Borg()
        >>> b2 = Borg()
        >>> b1.value = 42
        >>> b2.value  # Will be 42, state is shared
        42
    """

    __shared_state = {}

    def __init__(self):
        """Initialize a new Borg instance with shared state.

        Sets the instance's ``__dict__`` to the shared state dictionary,
        ensuring all instances share the same state.
        """
        self.__dict__ = self.__shared_state


class LazyProperty:
    """Lazily instantiated property.

    Use this decorator when you want to set a property that will only be
    evaluated the first time it's accessed. This is useful for expensive
    computations that should be deferred until actually needed.

    Once computed, the value is stored as a regular attribute on the
    instance, avoiding repeated computation. Inspired by the discussion in
    the Stack Overflow thread below.

    :see: http://stackoverflow.com/questions/15226721/
    """

    def __init__(self, f_get):
        """Initialize the lazy property with a getter function.

        :param f_get: Function that computes the property value
        :type f_get: callable
        """
        self.f_get = f_get
        self.func_name = f_get.__name__

    def __get__(self, obj, cls):
        """Descriptor method to get the property value.

        :param obj: Instance the property is being accessed on
        :type obj: object or None
        :param cls: Class the property is defined on
        :type cls: type
        :returns: The computed property value
        :rtype: any
        """
        if obj is None:
            return None
        value = self.f_get(obj)
        setattr(obj, self.func_name, value)
        return value


class CallbackRegister:
    """Registers pickable functions to be executed later.

    This class maintains a registry of functions with their arguments
    that can be called at a later time, typically for cleanup operations.
    All registered functions must be pickable (serializable).
    """

    def __init__(self, name, log):
        """Initialize the callback register.

        :param name: Human readable identifier of this register
        :type name: str
        :param log: Logger instance for error reporting
        :type log: logging.Logger
        """
        self._name = name
        self._items = []
        self._log = log

    def register(self, func, args, kwargs, once=False):
        """Register function/args to be called on self.run().

        :param func: Pickable function to be called later
        :type func: callable
        :param args: Pickable positional arguments for the function
        :type args: tuple
        :param kwargs: Pickable keyword arguments for the function
        :type kwargs: dict
        :param once: Add unique (func,args,kwargs) combination only once
        :type once: bool
        """
        item = (func, args, kwargs)
        if not once or item not in self._items:
            self._items.append(item)

    def unregister(self, func, args, kwargs):
        """Unregister (func,args,kwargs) combination.

        :param func: Pickable function to unregister
        :type func: callable
        :param args: Pickable positional arguments
        :type args: tuple
        :param kwargs: Pickable keyword arguments
        :type kwargs: dict
        """
        item = (func, args, kwargs)
        if item in self._items:
            self._items.remove(item)

    def run(self):
        """Call all registered functions.

        Executes all registered functions with their associated arguments.
        If any function raises an exception, it is logged and execution
        continues with the remaining functions. Functions are called in
        LIFO order (last registered, first executed).
        """
        while self._items:
            item = self._items.pop()
            try:
                func, args, kwargs = item
                func(*args, **kwargs)
            except:  # Ignore all exceptions pylint: disable=W0702
                self._log.error(
                    "%s failed to destroy %s:\n%s", self._name, item, sys.exc_info()[1]
                )

    def __del__(self):
        """Destructor that runs all registered callbacks.

        .. warning::
           Always call self.run() manually, this is not guaranteed
           to be executed!
        """
        self.run()


def time_to_seconds(time):
    """Convert time in minutes, hours and days to seconds.

    Converts a time string with optional unit suffix to seconds.
    Supported units are 's' (seconds), 'm' (minutes), 'h' (hours),
    and 'd' (days). If no unit is specified, the value is assumed
    to be in seconds.

    :param time: Time, optionally including the unit (i.e. '10d', '5m', '30')
    :type time: str, int, or None
    :returns: Time converted to seconds
    :rtype: int
    :raises ValueError: If the time format is invalid

    Example::

        >>> time_to_seconds('10m')
        600
        >>> time_to_seconds('2h')
        7200
        >>> time_to_seconds('30')
        30
        >>> time_to_seconds(None)
        0
    """
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    if time is not None:
        try:
            unit = time[-1].lower()
            if unit in units:
                mult = units[unit]
                seconds = int(time[:-1]) * mult
            else:
                seconds = int(time)
        except (ValueError, TypeError) as exc:
            raise ValueError(
                f"Invalid value '{time}' for time. Use a string "
                f"with the number and optionally the time unit "
                f"(s, m, h or d)."
            ) from exc
    else:
        seconds = 0
    return seconds


class DataSize:
    """Data Size object with builtin unit-converted attributes.

    Represents a data size with automatic unit conversion capabilities.
    Supports bytes (b), kibibytes (k), mebibytes (m), gibibytes (g),
    and tebibytes (t). All conversions use binary multipliers (1024-based).

    :param data: Data size plus optional unit string. i.e. '10m'. No
                 unit string means the data size is in bytes.
    :type data: str, int, or float
    :raises InvalidDataSize: If the data format is invalid

    Example::

        >>> size = DataSize('10m')
        >>> size.b  # bytes
        10485760
        >>> size.k  # kibibytes
        10240
        >>> size.g  # gibibytes
        0
    """

    __slots__ = ["_value", "_unit"]

    MULTIPLIERS = {
        "b": 1,  # bytes (2**0)
        "k": 1024,  # kibibytes (2**10)
        "m": 1048576,  # mebibytes (2**20)
        "g": 1073741824,  # gibibytes (2**30)
        "t": 1099511627776,  # tebibytes (2**40)
    }

    def __init__(self, data):
        """Initialize a DataSize object.

        :param data: Data size with optional binary unit (e.g., '10M', '2.5G', '100')
        :type data: str, int, or float
        :raises InvalidDataSize: If the data format is invalid
        """
        try:
            norm = str(data).strip().lower()
            match = re.match(r"^(\d+(\.\d+)?)(?:\s*([bkmgt]))?$", norm)
            if not match:
                raise ValueError

            self._value = float(match.group(1))
            self._unit = match.group(3) or "b"

            if self._unit not in self.MULTIPLIERS or self._value < 0:
                raise ValueError

        except ValueError as exc:
            raise InvalidDataSize(
                f"Invalid data size '{data}'. Use binary unit formats like '10M', '2.5G', or '100'."
            ) from exc

    @property
    def value(self):
        """The numeric value of the data size.

        :returns: The original numeric value without unit conversion
        :rtype: float
        """
        return self._value

    @property
    def unit(self):
        """The unit of the data size.

        :returns: Single character representing the unit ('b', 'k', 'm', 'g', 't')
        :rtype: str
        """
        return self._unit

    @property
    def b(self):
        """Data size in bytes.

        :returns: Size converted to bytes
        :rtype: float
        """
        return self._value * self.MULTIPLIERS[self._unit]

    @property
    def k(self):
        """Data size in kibibytes.

        :returns: Size converted to kibibytes (truncated to integer)
        :rtype: int
        """
        return int(self._value * self.MULTIPLIERS[self._unit] / self.MULTIPLIERS["k"])

    @property
    def m(self):
        """Data size in mebibytes.

        :returns: Size converted to mebibytes (truncated to integer)
        :rtype: int
        """
        return int(self._value * self.MULTIPLIERS[self._unit] / self.MULTIPLIERS["m"])

    @property
    def g(self):
        """Data size in gibibytes.

        :returns: Size converted to gibibytes (truncated to integer)
        :rtype: int
        """
        return int(self._value * self.MULTIPLIERS[self._unit] / self.MULTIPLIERS["g"])

    @property
    def t(self):
        """Data size in tebibytes.

        :returns: Size converted to tebibytes (truncated to integer)
        :rtype: int
        """
        return int(self._value * self.MULTIPLIERS[self._unit] / self.MULTIPLIERS["t"])


# pylint: disable=wrong-import-position
from avocado.utils.deprecation import log_deprecation

log_deprecation.warning("data_structures")
