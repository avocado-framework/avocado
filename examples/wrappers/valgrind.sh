#!/bin/bash
#
# Run process inside valgrind's memcheck.
#

exec valgrind \
    --tool=memcheck \
    --verbose \
    --trace-children=yes \
    --leak-check=full \
    --log-file=$AVOCADO_TEST_LOGDIR/valgrind.log.$$ -- "$@"
