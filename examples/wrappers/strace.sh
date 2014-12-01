#!/bin/bash

exec strace -ff -o $AVOCADO_TEST_LOGDIR/strace.log -- $@
