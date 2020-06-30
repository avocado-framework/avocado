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
# Copyright: Red Hat Inc. 2020
# Authors: Beraldo Leal <bleal@redhat.com>


from shutil import get_terminal_size

COLUMNS, LINES = get_terminal_size((80, 23))


class FancyDots:
    colors = {'P':    '\033[92m',
              'S':    '\033[94m',
              's':    '\033[94m',
              '.':    '\033[94m',
              'F':    '\033[91m',
              'E':    '\033[91m',
              'ENDC': '\033[0m'}

    def __init__(self, number_of_tests):
        self.tests = ['.'] * number_of_tests

    def _make_color_line(self, line):
        result = ""
        for char in line:
            result += self.colors[char] + char + self.colors['ENDC']
        return result

    @staticmethod
    def _split_lines(line, columns=min(COLUMNS, 80)):
        return [line[i:i + columns] for i in range(0, len(line), columns)]

    def update_test(self, test_id, status='P'):
        self.tests[test_id-1] = status
        self.print_dots()

    def print_dots(self):
        print("\033c", end="")

        print("Avocado test progress (this is experimental):")
        for line in self._split_lines(self.tests):
            print(self._make_color_line(line))
