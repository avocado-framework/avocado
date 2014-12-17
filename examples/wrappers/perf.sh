#!/bin/bash
#
# Record process information with perf.
#

exec perf record \
    --quiet \
    -o $AVOCADO_TEST_LOGDIR/perf.data.$$ -- "$@"
