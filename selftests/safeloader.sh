#!/bin/bash -e

SAFELOADER_OUTPUT=$(mktemp /tmp/safeloader-XXXXXX)
DEFAULT_LOADER_OUTPUT=$(mktemp /tmp/safeloader-XXXXXX)

function cleanup()
{
    rm $SAFELOADER_OUTPUT $DEFAULT_LOADER_OUTPUT
}

trap cleanup EXIT

for PYTHON_FILE in $(grep -c -m1 -E 'import unittest$' selftests/unit{,/plugin,/utils}/test_*.py selftests/functional{,/plugin}/test_*.py | grep -v -E ':0$' | cut -d ':' -f 1); do
    echo "*** Checking safeloader on $PYTHON_FILE ***";
    python3 contrib/scripts/find-python-unittest $PYTHON_FILE > $SAFELOADER_OUTPUT;
    AVOCADO_SAFELOADER_UNITTEST_ORDER_COMPAT=1 python3 contrib/scripts/avocado-safeloader-find-python-unittest $PYTHON_FILE > $DEFAULT_LOADER_OUTPUT;
    diff -u $SAFELOADER_OUTPUT $DEFAULT_LOADER_OUTPUT;
done;
