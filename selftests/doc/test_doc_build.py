"""
Build documentation and report whether we had warning/error messages.

This is geared towards documentation build regression testing.
"""
import os
import urllib
import unittest

from avocado.utils import process


basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
basedir = os.path.abspath(basedir)


class DocBuildError(Exception):
    pass


def has_no_external_connectivity():
    """
    Check condition for building the docs with Sphinx

    Sphinx will attempt to fetch the Python objects inventory during the build
    process. If for some reason, this test is being run on a machine that can
    not access that address simply because of network restrictions (or the
    developer may simply be on a plane) then it's better to SKIP the test than
    to give a false positive.
    """
    try:
        urllib.urlopen('http://docs.python.org/objects.inv')
        return False
    except:
        return True


class DocBuildTest(unittest.TestCase):

    @unittest.skipIf(has_no_external_connectivity(), "No external connectivity")
    def test_build_docs(self):
        """
        Build avocado HTML docs, reporting failures
        """
        ignore_list = []
        failure_lines = []
        # Disregard bogus warnings due to a bug in older versions of
        # python-sphinx.
        ignore_list.append('WARNING: toctree contains reference to ' +
                           'nonexisting document u\'api/test/avocado.core\'')
        ignore_list.append('WARNING: toctree contains reference to ' +
                           'nonexisting document u\'api/test/avocado.plugins\'')
        ignore_list.append('WARNING: toctree contains reference to ' +
                           'nonexisting document u\'api/test/avocado.utils\'')
        doc_dir = os.path.join(basedir, 'docs')
        process.run('make -C %s clean' % doc_dir)
        result = process.run('make -C %s html' % doc_dir, ignore_status=True)
        self.assertFalse(result.exit_status, "Doc build reported non-zero "
                         "status:\n%s" % result)
        stdout = result.stdout.splitlines()
        stderr = result.stderr.splitlines()
        output_lines = stdout + stderr
        for line in output_lines:
            ignore_msg = False
            for ignore in ignore_list:
                if ignore in line:
                    print('Expected warning ignored: %s' % line)
                    ignore_msg = True
            if ignore_msg:
                continue
            if 'ERROR' in line:
                failure_lines.append(line)
            if 'WARNING' in line:
                failure_lines.append(line)
        if failure_lines:
            e_msg = ('%s ERRORS and/or WARNINGS detected while building the html docs:\n' %
                     len(failure_lines))
            for (index, failure_line) in enumerate(failure_lines):
                e_msg += "%s) %s\n" % (index + 1, failure_line)
            e_msg += ('Full output: %s\n' % '\n'.join(output_lines))
            e_msg += 'Please check the output and fix your docstrings/.rst docs'
            raise DocBuildError(e_msg)


if __name__ == '__main__':
    unittest.main()
