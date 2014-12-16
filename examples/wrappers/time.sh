#!/bin/bash
#
# Run process inside time.
#

exec /usr/bin/time -o $AVOCADO_TEST_LOGDIR/time.log.$$ -- "$@"
