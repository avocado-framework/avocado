#!/bin/bash

valgrind \
    --tool=memcheck \
    --verbose \
    --trace-children=yes \
    --leak-check=full \
    --log-file=$AVOCADO_TEST_LOGDIR/valgrind.log.$$ -- $@
