#!/bin/bash
#
# Record deterministic execution using rr (http://rr-project.org)
#

export _RR_TRACE_DIR="$AVOCADO_TEST_OUTPUTDIR/rr"
mkdir -p "$_RR_TRACE_DIR"
exec rr record -n "$@"

