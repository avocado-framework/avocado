#!/bin/bash

exec perf record -o $AVOCADO_TEST_LOGDIR/perf.data.$$ -- $@
