#! /bin/bash -e
#
# shell command line helper, wrap command line ops to avocado friendly way
#
# Example:  avocado-run-inplace.sh dnf update -y
#

status=1

while [ "$1" != "" ]; do
	case $1 in
		--keep)
			keep=1
			;;
		*)
			break
	esac
	shift
done

tmp=`mktemp -d /tmp/XXXXXXX`
cmd="$@"
script_name="${cmd//[^[:alnum:]-]/_}.sh"

echo '#!/bin/sh' > $tmp/$script_name
echo "pushd `pwd`" >> $tmp/$script_name
echo "$@" >> $tmp/$script_name

ln -s /bin/sh $tmp/sh
avocado run --external-runner=$tmp/sh --external-runner-chdir=runner $script_name
status=$?

if test -z "$keep"; then
	unlink $tmp/$script_name
	unlink $tmp/sh
	rmdir $tmp
fi
exit $status
