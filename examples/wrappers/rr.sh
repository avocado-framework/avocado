#!/bin/bash
#
# Record deterministic execution using rr
#

export _RR_TRACE_DIR=$AVOCADO_TEST_LOGDIR/rr
mkdir -p $_RR_TRACE_DIR
exec rr record "$@"

