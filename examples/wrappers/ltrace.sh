#!/bin/bash
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: Red Hat Inc. 2014
# Author: Ruda Moura <rmoura@redhat.com>

# Map interesting signals to exit codes (see kill -L)
# Example: SIGHUP (kill -1) 128+1 = 129

declare -A signal_map
signal_map[SIGHUP]=129
signal_map[SIGINT]=130
signal_map[SIGQUIT]=131
signal_map[SIGILL]=132
signal_map[SIGTRAP]=133
signal_map[SIGABRT]=134
signal_map[SIGBUS]=135
signal_map[SIGFPE]=136
signal_map[SIGKILL]=137
signal_map[SIGUSR1]=138
signal_map[SIGSEGV]=139
signal_map[SIGUSR2]=140
signal_map[SIGPIPE]=141
signal_map[SIGALRM]=142
signal_map[SIGTERM]=143
signal_map[SIGSTKFLT]=144
signal_map[SIGSTKFLT]=144
signal_map[SIGXCPU]=152
signal_map[SIGXFSZ]=153
signal_map[SIGVTALRM]=154
signal_map[SIGPROF]=155
signal_map[SIGIO]=157
signal_map[SIGPWR]=158
signal_map[SIGSYS]=159
signal_map[UNKNOWN_SIGNAL]=160

ltrace -f -o $AVOCADO_TEST_LOGDIR/ltrace.log.$$ -- $@

signal_name=$(sed -ne 's/^.*+++ killed by \([A-Z_]\+\) +++$/\1/p' $AVOCADO_TEST_LOGDIR/ltrace.log.$$)
if [ -n "$signal_name" ] ; then
    exit ${signal_map[$signal_name]}
fi

exit_status=$(sed -ne 's/^.*+++ exited (status \([0-9]\+\)) +++$/\1/p' $AVOCADO_TEST_LOGDIR/ltrace.log.$$)
if [ -n "$exit_status" ] ; then
    exit $exit_status
fi

exit 0
