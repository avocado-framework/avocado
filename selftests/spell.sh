#!/bin/sh -e
pylint -j 1 --errors-only --disable=all --enable=spelling --spelling-dict=en_US --spelling-private-dict-file=spell.ignore *
