#!/usr/bin/python
"""
Build documentation and report whether we had warning/error messages.

This is geared towards documentation build regression testing.
"""
import os
import sys

# simple magic for using scripts within a source tree
basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')
basedir = os.path.abspath(basedir)
if os.path.isdir(os.path.join(basedir, 'avocado')):
    sys.path.append(basedir)

from avocado.utils import process


class DocBuildError(Exception):
    pass


def test_build_docs():
    """
    Build avocado HTML docs, reporting failures
    """
    ignore_list = []
    failure_lines = []
    doc_dir = os.path.join(basedir, 'docs')
    process.run('make -C %s clean' % doc_dir)
    result = process.run('make -C %s html' % doc_dir)
    stdout = result.stdout.splitlines()
    stderr = result.stderr.splitlines()
    output_lines = stdout + stderr
    for line in output_lines:
        ignore_msg = False
        for ignore in ignore_list:
            if ignore in line:
                print 'Expected warning ignored: %s' % line
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
    test_build_docs()
