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

"""
Plugin to run Test Anything Protocol tests in Avocado
"""

from collections import namedtuple
import enum
import io
import os
import re

from avocado.utils import process

from avocado.core import defaults
from avocado.core import exceptions
from avocado.core import loader
from avocado.core import output
from avocado.core import test
from avocado.core.plugin_interfaces import CLI
from avocado.core.plugin_interfaces import Resolver
from avocado.core.resolver import check_file
from avocado.core.resolver import ReferenceResolution
from avocado.core.resolver import ReferenceResolutionResult
from avocado.core.nrunner import Runnable


@enum.unique
class TestResult(enum.Enum):
    PASS = 'PASS'
    SKIP = 'SKIP'
    FAIL = 'FAIL'
    XFAIL = 'XFAIL'
    XPASS = 'XPASS'


# TapParser is based on Meson's TAP parser, which were licensed under the
# MIT (X11) license and were contributed to both Meson and Avocado by the
# same author (Paolo).

class TapParser:
    Plan = namedtuple('Plan', ['count', 'late', 'skipped', 'explanation'])
    Bailout = namedtuple('Bailout', ['message'])
    Test = namedtuple('Test', ['number', 'name', 'result', 'explanation'])
    Error = namedtuple('Error', ['message'])
    Version = namedtuple('Version', ['version'])

    _MAIN = 1
    _AFTER_TEST = 2
    _YAML = 3

    _RE_BAILOUT = re.compile(r'Bail out!\s*(.*)')
    _RE_DIRECTIVE = re.compile(r'(?:\s*\#\s*([Ss][Kk][Ii][Pp]\S*|[Tt][Oo][Dd][Oo])\b\s*(.*))?')
    _RE_PLAN = re.compile(r'1\.\.([0-9]+)' + _RE_DIRECTIVE.pattern)
    _RE_TEST = re.compile(r'((?:not )?ok)\s*(?:([0-9]+)\s*)?([^#]*)' + _RE_DIRECTIVE.pattern)
    _RE_VERSION = re.compile(r'TAP version ([0-9]+)')
    _RE_YAML_START = re.compile(r'(\s+)---.*')
    _RE_YAML_END = re.compile(r'\s+\.\.\.\s*')

    def __init__(self, tap_io):
        self.tap_io = tap_io

    def parse_test(self, ok, num, name, directive, explanation):
        name = name.strip()
        explanation = explanation.strip() if explanation else None
        if directive is not None:
            directive = directive.upper()
            if directive == 'SKIP':
                if ok:
                    yield self.Test(num, name, TestResult.SKIP, explanation)
                    return
            elif directive == 'TODO':
                result = TestResult.XPASS if ok else TestResult.XFAIL
                yield self.Test(num, name, result, explanation)
                return
            else:
                yield self.Error('invalid directive "%s"' % (directive,))

        result = TestResult.PASS if ok else TestResult.FAIL
        yield self.Test(num, name, result, explanation)

    def parse(self):
        found_late_test = False
        bailed_out = False
        plan = None
        lineno = 0
        num_tests = 0
        yaml_lineno = 0
        yaml_indent = ''
        state = self._MAIN
        version = 12
        while True:
            lineno += 1
            try:
                line = next(self.tap_io).rstrip()
            except StopIteration:
                break

            # YAML blocks are only accepted after a test
            if state == self._AFTER_TEST:
                if version >= 13:
                    m = self._RE_YAML_START.match(line)
                    if m:
                        state = self._YAML
                        yaml_lineno = lineno
                        yaml_indent = m.group(1)
                        continue
                state = self._MAIN

            elif state == self._YAML:
                if self._RE_YAML_END.match(line):
                    state = self._MAIN
                    continue
                if line.startswith(yaml_indent):
                    continue
                yield self.Error('YAML block not terminated (started on line %d)' % (yaml_lineno,))
                state = self._MAIN

            assert state == self._MAIN
            if line.startswith('#'):
                continue

            m = self._RE_TEST.match(line)
            if m:
                if plan and plan.late and not found_late_test:
                    yield self.Error('unexpected test after late plan')
                    found_late_test = True
                num_tests += 1
                num = num_tests if m.group(2) is None else int(m.group(2))
                if num != num_tests:
                    yield self.Error('out of order test numbers')
                yield from self.parse_test(m.group(1) == 'ok', num,
                                           m.group(3), m.group(4), m.group(5))
                state = self._AFTER_TEST
                continue

            m = self._RE_PLAN.match(line)
            if m:
                if plan:
                    yield self.Error('more than one plan found')
                else:
                    count = int(m.group(1))
                    skipped = (count == 0)
                    if m.group(2):
                        if m.group(2).upper().startswith('SKIP'):
                            if count > 0:
                                yield self.Error('invalid SKIP directive for plan')
                            skipped = True
                        else:
                            yield self.Error('invalid directive for plan')
                    plan = self.Plan(count=count, late=(num_tests > 0),
                                     skipped=skipped, explanation=m.group(3))
                    yield plan
                continue

            m = self._RE_BAILOUT.match(line)
            if m:
                yield self.Bailout(m.group(1))
                bailed_out = True
                continue

            m = self._RE_VERSION.match(line)
            if m:
                # The TAP version is only accepted as the first line
                if lineno != 1:
                    yield self.Error('version number must be on the first line')
                    continue
                version = int(m.group(1))
                if version < 13:
                    yield self.Error('version number should be at least 13')
                else:
                    yield self.Version(version=version)
                continue

            if line == '':
                continue

            yield self.Error('unexpected input at line %d' % (lineno,))

        if state == self._YAML:
            yield self.Error('YAML block not terminated (started on line %d)' % (yaml_lineno,))

        if not bailed_out and plan and num_tests != plan.count:
            if num_tests < plan.count:
                yield self.Error('Too few tests run (expected %d, got %d)'
                                 % (plan.count, num_tests))
            else:
                yield self.Error('Too many tests run (expected %d, got %d)'
                                 % (plan.count, num_tests))


class TapTest(test.SimpleTest):

    """
    Run a test command as a TAP test.
    """

    def _execute_cmd(self):
        try:
            test_params = {str(key): str(val)
                           for _, key, val in self.params.iteritems()}

            result = process.run(self._command, verbose=True,
                                 allow_output_check='stdout',
                                 env=test_params, encoding=defaults.ENCODING)

            self._log_detailed_cmd_info(result)
        except process.CmdError as details:
            self._log_detailed_cmd_info(details.result)
            raise exceptions.TestFail(details)

        if result.exit_status != 0:
            self.fail('TAP Test execution returned a '
                      'non-0 exit code (%s)' % result)
        parser = TapParser(io.StringIO(result.stdout_text))
        fail = 0
        count = 0
        bad_errormsg = 'there were test failures'
        for event in parser.parse():
            if isinstance(event, TapParser.Error):
                self.error('TAP parsing error: ' + event.message)
                continue
            if isinstance(event, TapParser.Bailout):
                self.error(event.message)
                continue
            if isinstance(event, TapParser.Test):
                bad = event.result in (TestResult.XPASS, TestResult.FAIL)
                if event.result != TestResult.SKIP:
                    count += 1
                if bad:
                    self.log.error('%s %s %s', event.result.name, event.number, event.name)
                    fail += 1
                    if event.result == TestResult.XPASS:
                        bad_errormsg = 'there were test failures or unexpected passes'
                else:
                    self.log.info('%s %s %s', event.result.name, event.number, event.name)

        if not count:
            raise exceptions.TestSkipError('no tests were run')
        if fail:
            self.fail(bad_errormsg)


class TapLoader(loader.SimpleFileLoader):
    """
    Test Anything Protocol loader class
    """
    name = "tap"

    @staticmethod
    def get_type_label_mapping():
        mapping = loader.SimpleFileLoader.get_type_label_mapping()
        mapping.update(
            {TapTest: 'TAP'})
        return mapping

    @staticmethod
    def get_decorator_mapping():
        mapping = loader.SimpleFileLoader.get_decorator_mapping()
        mapping.update(
            {TapTest: output.TERM_SUPPORT.healthy_str})
        return mapping

    def _make_simple_test(self, test_path, subtests_filter):
        return self._make_test(TapTest, test_path,
                               subtests_filter=subtests_filter,
                               executable=test_path)


class TapResolver(Resolver):

    name = 'tap'
    description = 'Test resolver for executable files to be handled as tests'

    @staticmethod
    def resolve(reference):

        criteria_check = check_file(reference, reference, suffix=None,
                                    type_name='executable file',
                                    access_check=os.R_OK | os.X_OK,
                                    access_name='executable')
        if criteria_check is not True:
            return criteria_check

        return ReferenceResolution(reference,
                                   ReferenceResolutionResult.SUCCESS,
                                   [Runnable('tap', reference)])


class TapCLI(CLI):

    """
    Run Test Anything Protocol tests
    """

    name = 'tap'
    description = "Test Anything Protocol options for 'run' subcommand"

    def configure(self, parser):
        pass

    def run(self, config):
        loader.loader.register_plugin(TapLoader)
