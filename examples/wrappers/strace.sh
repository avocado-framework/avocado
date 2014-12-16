#!/bin/bash
#
# Run process inside strace.
#

exec strace -ff -o $AVOCADO_TEST_LOGDIR/strace.log -- "$@"
