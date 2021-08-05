#!/bin/bash -e

SAFELOADER_OUTPUT=$(mktemp /tmp/safeloader-XXXXXX)
DEFAULT_LOADER_OUTPUT=$(mktemp /tmp/safeloader-XXXXXX)

function cleanup()
{
    rm $SAFELOADER_OUTPUT $DEFAULT_LOADER_OUTPUT
}

trap cleanup EXIT

function check()
{
    echo "*** Checking safeloader on $1 ***";
    python3 contrib/scripts/find-python-unittest $1 > $SAFELOADER_OUTPUT;
    AVOCADO_SAFELOADER_UNITTEST_ORDER_COMPAT=1 python3 contrib/scripts/avocado-safeloader-find-python-unittest $1 > $DEFAULT_LOADER_OUTPUT;
    diff -u $SAFELOADER_OUTPUT $DEFAULT_LOADER_OUTPUT;
}

for input_file in $(grep -c -m1 -E 'import unittest$' selftests/unit{,/plugin,/utils}/test_*.py selftests/functional{,/plugin}/test_*.py | grep -v -E ':0$' | cut -d ':' -f 1); do
    check input_file
done
