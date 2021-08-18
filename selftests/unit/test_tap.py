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
# Copyright: Red Hat Inc. 2019
# Authors: Paolo Bonzini <pbonzini@redhat.com>

import io
import unittest

from avocado.core.tapparser import TapParser, TestResult

# The TapParser unit tests are based on Meson's unit tests for TAP parsing,
# which were licensed under the MIT (X11) license and were contributed to
# both Meson and Avocado by the same author (Paolo).


class TapParserTests(unittest.TestCase):
    def assert_test(self, events, **kwargs):
        if 'explanation' not in kwargs:
            kwargs['explanation'] = None
        self.assertEqual(next(events), TapParser.Test(**kwargs))

    def assert_plan(self, events, **kwargs):
        if 'skipped' not in kwargs:
            kwargs['skipped'] = False
        if 'explanation' not in kwargs:
            kwargs['explanation'] = None
        self.assertEqual(next(events), TapParser.Plan(**kwargs))

    def assert_version(self, events, **kwargs):
        self.assertEqual(next(events), TapParser.Version(**kwargs))

    def assert_error(self, events):
        self.assertEqual(type(next(events)), TapParser.Error)

    def assert_bailout(self, events, **kwargs):
        self.assertEqual(next(events), TapParser.Bailout(**kwargs))

    def assert_last(self, events):
        with self.assertRaises(StopIteration):
            next(events)

    def parse_tap(self, s):
        parser = TapParser(io.StringIO(s))
        return iter(parser.parse())

    def parse_tap_v13(self, s):
        events = self.parse_tap('TAP version 13\n' + s)
        self.assert_version(events, version=13)
        return events

    def test_empty(self):
        events = self.parse_tap('')
        self.assert_last(events)

    def test_empty_plan(self):
        events = self.parse_tap('1..0')
        self.assert_plan(events, count=0, late=False, skipped=True)
        self.assert_last(events)

    def test_plan_directive(self):
        events = self.parse_tap('1..0 # skipped for some reason')
        self.assert_plan(events, count=0, late=False, skipped=True,
                         explanation='for some reason')
        self.assert_last(events)

        events = self.parse_tap('1..1 # skipped for some reason\nok 1')
        self.assert_error(events)
        self.assert_plan(events, count=1, late=False, skipped=True,
                         explanation='for some reason')
        self.assert_test(events, number=1, name='', result=TestResult.PASS)
        self.assert_last(events)

        events = self.parse_tap('1..1 # todo not supported here\nok 1')
        self.assert_error(events)
        self.assert_plan(events, count=1, late=False, skipped=False,
                         explanation='not supported here')
        self.assert_test(events, number=1, name='', result=TestResult.PASS)
        self.assert_last(events)

    def test_one_test_ok(self):
        events = self.parse_tap('ok')
        self.assert_test(events, number=1, name='', result=TestResult.PASS)
        self.assert_last(events)

    def test_one_test_with_number(self):
        events = self.parse_tap('ok 1')
        self.assert_test(events, number=1, name='', result=TestResult.PASS)
        self.assert_last(events)

    def test_one_test_with_name(self):
        events = self.parse_tap('ok 1 abc')
        self.assert_test(events, number=1, name='abc', result=TestResult.PASS)
        self.assert_last(events)

    def test_one_test_not_ok(self):
        events = self.parse_tap('not ok')
        self.assert_test(events, number=1, name='', result=TestResult.FAIL)
        self.assert_last(events)

    def test_one_test_todo(self):
        events = self.parse_tap('not ok 1 abc # TODO')
        self.assert_test(events, number=1, name='abc', result=TestResult.XFAIL)
        self.assert_last(events)

        events = self.parse_tap('ok 1 abc # TODO')
        self.assert_test(events, number=1, name='abc', result=TestResult.XPASS)
        self.assert_last(events)

    def test_one_test_skip(self):
        events = self.parse_tap('ok 1 abc # SKIP')
        self.assert_test(events, number=1, name='abc', result=TestResult.SKIP)
        self.assert_last(events)

    def test_one_test_skip_failure(self):
        events = self.parse_tap('not ok 1 abc # SKIP')
        self.assert_test(events, number=1, name='abc', result=TestResult.FAIL)
        self.assert_last(events)

    def test_many_early_plan(self):
        events = self.parse_tap('1..4\nok 1\nnot ok 2\nok 3\nnot ok 4')
        self.assert_plan(events, count=4, late=False)
        self.assert_test(events, number=1, name='', result=TestResult.PASS)
        self.assert_test(events, number=2, name='', result=TestResult.FAIL)
        self.assert_test(events, number=3, name='', result=TestResult.PASS)
        self.assert_test(events, number=4, name='', result=TestResult.FAIL)
        self.assert_last(events)

    def test_many_late_plan(self):
        events = self.parse_tap('ok 1\nnot ok 2\nok 3\nnot ok 4\n1..4')
        self.assert_test(events, number=1, name='', result=TestResult.PASS)
        self.assert_test(events, number=2, name='', result=TestResult.FAIL)
        self.assert_test(events, number=3, name='', result=TestResult.PASS)
        self.assert_test(events, number=4, name='', result=TestResult.FAIL)
        self.assert_plan(events, count=4, late=True)
        self.assert_last(events)

    def test_directive_case(self):
        events = self.parse_tap('ok 1 abc # skip')
        self.assert_test(events, number=1, name='abc', result=TestResult.SKIP)
        self.assert_last(events)

        events = self.parse_tap('ok 1 abc # ToDo')
        self.assert_test(events, number=1, name='abc', result=TestResult.XPASS)
        self.assert_last(events)

    def test_directive_explanation(self):
        events = self.parse_tap('ok 1 abc # skip why')
        self.assert_test(events, number=1, name='abc', result=TestResult.SKIP,
                         explanation='why')
        self.assert_last(events)

        events = self.parse_tap('ok 1 abc # ToDo Because')
        self.assert_test(events, number=1, name='abc', result=TestResult.XPASS,
                         explanation='Because')
        self.assert_last(events)

    def test_one_test_early_plan(self):
        events = self.parse_tap('1..1\nok')
        self.assert_plan(events, count=1, late=False)
        self.assert_test(events, number=1, name='', result=TestResult.PASS)
        self.assert_last(events)

    def test_one_test_late_plan(self):
        events = self.parse_tap('ok\n1..1')
        self.assert_test(events, number=1, name='', result=TestResult.PASS)
        self.assert_plan(events, count=1, late=True)
        self.assert_last(events)

    def test_out_of_order(self):
        events = self.parse_tap('ok 2')
        self.assert_error(events)
        self.assert_test(events, number=2, name='', result=TestResult.PASS)
        self.assert_last(events)

    def test_middle_plan(self):
        events = self.parse_tap('ok 1\n1..2\nok 2')
        self.assert_test(events, number=1, name='', result=TestResult.PASS)
        self.assert_plan(events, count=2, late=True)
        self.assert_error(events)
        self.assert_test(events, number=2, name='', result=TestResult.PASS)
        self.assert_last(events)

    def test_too_many_plans(self):
        events = self.parse_tap('1..1\n1..2\nok 1')
        self.assert_plan(events, count=1, late=False)
        self.assert_error(events)
        self.assert_test(events, number=1, name='', result=TestResult.PASS)
        self.assert_last(events)

    def test_too_many(self):
        events = self.parse_tap('ok 1\nnot ok 2\n1..1')
        self.assert_test(events, number=1, name='', result=TestResult.PASS)
        self.assert_test(events, number=2, name='', result=TestResult.FAIL)
        self.assert_plan(events, count=1, late=True)
        self.assert_error(events)
        self.assert_last(events)

        events = self.parse_tap('1..1\nok 1\nnot ok 2')
        self.assert_plan(events, count=1, late=False)
        self.assert_test(events, number=1, name='', result=TestResult.PASS)
        self.assert_test(events, number=2, name='', result=TestResult.FAIL)
        self.assert_error(events)
        self.assert_last(events)

    def test_too_few(self):
        events = self.parse_tap('ok 1\nnot ok 2\n1..3')
        self.assert_test(events, number=1, name='', result=TestResult.PASS)
        self.assert_test(events, number=2, name='', result=TestResult.FAIL)
        self.assert_plan(events, count=3, late=True)
        self.assert_error(events)
        self.assert_last(events)

        events = self.parse_tap('1..3\nok 1\nnot ok 2')
        self.assert_plan(events, count=3, late=False)
        self.assert_test(events, number=1, name='', result=TestResult.PASS)
        self.assert_test(events, number=2, name='', result=TestResult.FAIL)
        self.assert_error(events)
        self.assert_last(events)

    def test_too_few_bailout(self):
        events = self.parse_tap('1..3\nok 1\nnot ok 2\nBail out! no third test')
        self.assert_plan(events, count=3, late=False)
        self.assert_test(events, number=1, name='', result=TestResult.PASS)
        self.assert_test(events, number=2, name='', result=TestResult.FAIL)
        self.assert_bailout(events, message='no third test')
        self.assert_last(events)

    def test_diagnostics(self):
        events = self.parse_tap('1..1\n# ignored\nok 1')
        self.assert_plan(events, count=1, late=False)
        self.assert_test(events, number=1, name='', result=TestResult.PASS)
        self.assert_last(events)

        events = self.parse_tap('# ignored\n1..1\nok 1\n# ignored too')
        self.assert_plan(events, count=1, late=False)
        self.assert_test(events, number=1, name='', result=TestResult.PASS)
        self.assert_last(events)

        events = self.parse_tap('# ignored\nok 1\n1..1\n# ignored too')
        self.assert_test(events, number=1, name='', result=TestResult.PASS)
        self.assert_plan(events, count=1, late=True)
        self.assert_last(events)

    def test_empty_line(self):
        events = self.parse_tap('1..1\n\nok 1')
        self.assert_plan(events, count=1, late=False)
        self.assert_test(events, number=1, name='', result=TestResult.PASS)
        self.assert_last(events)

    def test_unexpected(self):
        events = self.parse_tap('1..1\ninvalid\nok 1')
        self.assert_plan(events, count=1, late=False)
        self.assert_test(events, number=1, name='', result=TestResult.PASS)
        self.assert_last(events)

    def test_version(self):
        events = self.parse_tap('TAP version 13\n')
        self.assert_version(events, version=13)
        self.assert_last(events)

        events = self.parse_tap('TAP version 12\n')
        self.assert_error(events)
        self.assert_last(events)

        events = self.parse_tap('1..0\nTAP version 13\n')
        self.assert_plan(events, count=0, late=False, skipped=True)
        self.assert_error(events)
        self.assert_last(events)

    def test_yaml(self):
        events = self.parse_tap_v13('ok\n ---\n foo: abc\n  bar: def\n ...\nok 2')
        self.assert_test(events, number=1, name='', result=TestResult.PASS)
        self.assert_test(events, number=2, name='', result=TestResult.PASS)
        self.assert_last(events)

        events = self.parse_tap_v13('ok\n ---\n foo: abc\n  bar: def')
        self.assert_test(events, number=1, name='', result=TestResult.PASS)
        self.assert_error(events)
        self.assert_last(events)

        events = self.parse_tap_v13('ok 1\n ---\n foo: abc\n  bar: def\nnot ok 2')
        self.assert_test(events, number=1, name='', result=TestResult.PASS)
        self.assert_error(events)
        self.assert_test(events, number=2, name='', result=TestResult.FAIL)
        self.assert_last(events)


if __name__ == '__main__':
    unittest.main()
