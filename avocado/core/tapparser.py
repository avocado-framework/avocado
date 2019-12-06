import enum
import re
from collections import namedtuple


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
