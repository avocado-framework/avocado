#!/usr/bin/python
__all__ = ['MAJOR', 'MINOR', 'RELEASE', 'VERSION']


MAJOR = 0
MINOR = 1
RELEASE = 0

VERSION = "%s.%s.%s" % (MAJOR, MINOR, RELEASE)

if __name__ == '__main__':
    print VERSION
