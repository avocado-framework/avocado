#!/bin/sh -e
echo "** Running spell check..."

PYLINT=$(which pylint-3 2>/dev/null || which pylint)

${PYLINT} -j 1 --errors-only --disable=all --enable=spelling --spelling-dict=en_US --spelling-private-dict-file=spell.ignore *
