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
# This code was inspired in the autotest project,
#
# client/shared/utils.py
# Original author: Cleber Rosa <crosa@redhat.com>
#
# Copyright: Red Hat Inc. 2015
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>

"""Utility functions for user friendly display of information."""

import sys


def display_data_size(size):
    """Display data size in human readable units (SI).

    :param size: Data size, in Bytes.
    :type size: int
    :return: Human readable string with data size, using SI prefixes.
    :rtype: str
    """
    prefixes = ["B", "KB", "MB", "GB", "TB", "PB"]
    factor = float(1000)
    i = 0
    while size >= factor:
        if i >= len(prefixes) - 1:
            break
        size /= factor
        i += 1

    return f"{size:.2f} {prefixes[i]}"


class ProgressBar:
    """Displays interactively the progress of a given task.

    Inspired/adapted from https://gist.github.com/t0xicCode/3306295
    """

    def __init__(self, minimum=0, maximum=100, width=75, title=""):
        """Initializes a new progress bar.

        :param minimum: Minimum (initial) value on the progress bar
        :type minimum: int
        :param maximum: Maximum (final) value on the progress bar
        :type maximum: int
        :param width: Number of columns, that is screen width
        :type width: int
        :param title: Optional title to display with the progress bar
        :type title: str
        :raises AssertionError: When maximum is not greater than minimum
        """
        assert maximum > minimum

        self.prog_bar = ""
        self.old_prog_bar = ""

        if title:
            width -= len(title)

        self.minimum = minimum
        self.maximum = maximum
        self.width = width
        self.title = title

        self.current_amount = minimum
        self.update_amount(minimum)

    def append_amount(self, amount):
        """Increments the current amount value by the specified amount.

        :param amount: The value to add to the current amount
        :type amount: int or float
        """
        self.update_amount(self.current_amount + amount)

    def update_percentage(self, percentage):
        """Updates the progress bar to the specified percentage value.

        :param percentage: The percentage value to set (0-100)
        :type percentage: int or float
        """
        self.update_amount((percentage * float(self.maximum)) / 100.0)

    def update_amount(self, amount):
        """Performs sanity checks and updates the current amount value.

        The amount is clamped between the minimum and maximum values set
        during initialization. After updating the amount, the progress bar
        is refreshed and redrawn.

        :param amount: The new amount value to set
        :type amount: int or float
        """
        amount = max(amount, self.minimum)
        amount = min(amount, self.maximum)
        self.current_amount = amount

        self._update_progress_bar()
        self.draw()

    def _update_progress_bar(self):
        """Builds the actual progress bar text representation.

        This internal method calculates the percentage completion,
        creates the visual bar with '=' characters and '>' indicator,
        and formats the display string including the percentage and
        optional title.
        """
        diff = float(self.current_amount - self.minimum)
        done = (diff / float(self.maximum - self.minimum)) * 100.0
        done = int(round(done))

        all_full = self.width - 2
        hashes = (done / 100.0) * all_full
        hashes = int(round(hashes))

        if not hashes:
            screen_text = f"[>{' ' * (all_full - 1)}]"
        elif hashes == all_full:
            screen_text = f"[{'=' * all_full}]"
        else:
            screen_text = f"[{'=' * (hashes - 1)}>{' ' * (all_full - hashes)}]"

        percent_string = str(done) + "%"

        # slice the percentage into the bar
        screen_text = " ".join([screen_text, percent_string])

        if self.title:
            screen_text = f"{self.title}: {screen_text}"
        self.prog_bar = screen_text

    def draw(self):
        """Prints the updated progress bar text to the screen.

        Only prints when the progress bar has changed from the previous
        state to avoid unnecessary screen updates. Uses carriage return
        to overwrite the previous progress bar on the same line.
        """
        if self.prog_bar != self.old_prog_bar:
            self.old_prog_bar = self.prog_bar
            sys.stdout.write("\r" + self.prog_bar)
            sys.stdout.flush()

    def __str__(self):
        """Returns the current progress bar as a string.

        :return: The formatted progress bar string
        :rtype: str
        """
        return str(self.prog_bar)


# pylint: disable=wrong-import-position
from avocado.utils.deprecation import log_deprecation

log_deprecation.warning("output")
