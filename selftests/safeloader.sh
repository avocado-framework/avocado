#!/bin/bash -e

# This script tests the "avocado.core.safeloader" module by processing
# either one specific file (the first command line parameter given to
# this script) or all unittest-like files in the selftests directories

INPUT_FILE="${1:-}"
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

if [ -n "$INPUT_FILE" ]; then
    check "$INPUT_FILE";
else
    for input_file in $(grep -c -m1 -E 'import unittest$' selftests/unit{,/plugin,/utils}/test_*.py selftests/functional{,/plugin}/test_*.py | grep -v -E ':0$' | cut -d ':' -f 1); do
        check "$input_file"
    done
fi
