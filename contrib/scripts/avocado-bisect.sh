#!/bin/sh
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; specifically version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: 2017 Red Hat, Inc.
# Author: Lukas Doktor <ldoktor@redhat.com>

#
# This script helps with bisecting avocado sources by doing the prep
# and cleanup work needed to successfully bisect avocado execution
# Use it by running:
#     $ git bisect start $BAD $GOOD
#     $ git bisect run ./contrib/scripts/avocado-bisect.sh $YOUR_CMD
#

ERR=()
INTERACTIVE=0

case $1 in
    "-h")
    	echo "$0 [-h] [-i] [CHECK_CMD [...]]"
    	echo "    -h         Show this help"
        echo "    -i         On failure ask whether to ignore this failure"
        echo "    CHECK_CMD  Check cmd(s), when not supplied 'make check' is used"
        exit 1
        ;;
    "-i")
        shift
        INTERACTIVE=1
        ;;
esac


run() {
    echo -e "\n\e[32mRunning '$*'\e[0m"
    eval $*
    if [ $? != 0 ]; then
        if [ $INTERACTIVE -eq 1 ]; then
            echo -ne "\e[33mUse 'y' to ignore this failure: \e[0m"
            read RES
            [ "$RES" == "y" ] && echo -e "\e[33mStatus of $* overridden to PASS\[0m" && return 0
        fi
        echo -e "\e[31m$* FAILED\e[0m"
        ERR+=("$1")
    else
        echo -e "\e[32m$* PASSED\e[0m\n"
    fi
}

run "git log -1 --oneline"
run "make develop"
if [ "$*" ]; then
    run $*
else
	run "make check"
fi
run "make clean"


if [ "$ERR" ]; then
    echo -e "\e[31m"
    echo "Failed checks of commit $(git log -1 --oneline):"
    for CMD in "${ERR[@]}"; do
        echo -e " * $CMD FAILED"
    done
    echo -ne "\e[0m"
else
    echo -e "\e[32mAll checks PASSED\e[0m"
fi
if [ "$ERR" ]; then
    exit 1
fi
exit 0
