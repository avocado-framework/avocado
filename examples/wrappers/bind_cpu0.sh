#!/bin/bash
#
# Bind process to CPU 0.
#

exec taskset -c 0 "$@"
