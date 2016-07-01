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
# Copyright: 2016 Red Hat, Inc.
# Author: Lukas Doktor <ldoktor@redhat.com>

#
# This script runs kvm-unit-tests as individual tests inside avocado.
# Optionally it downloads the kvm-unit-tests from git.
#

# Parse arguments
WILDCARD="*"
while [ true ]; do
    case $1 in
        "--endian")
            shift
            ENDIAN="--endian $1"
            ;;
        "--path")
            shift
            KVM_UNIT_TEST=$1
            ;;
        "--wildcard")
            shift
            WILDCARD="$1"
            ;;
        "-h"|"--help")
            echo "Usage: $0 [-h] [--endian ENDIAN] [--path PATH] [--wildcard WILDCARD] [avocado arguments ...]"
            echo
            echo "  -h          Show this help"
            echo "  --endian    Endian flag to kvm-unit-test configure"
            echo "  --path      Path to kvm-unit-test suite (default is tmp)"
            echo "  --wildcard  BASH Wildcard to select tests (by default all)"
            echo
            echo "Note: You might need to set ACCEL and/or QEMU env variables."
            exit 1
            ;;
        *)
            break
    esac
    shift
done

# Initialize directory and download kvm-unit-test if necessary
[ "$KVM_UNIT_TEST" ] || KVM_UNIT_TEST="$(mktemp -d)"
[ -d "$KVM_UNIT_TEST" ] || { mkdir -p "$KVM_UNIT_TEST"; CLEAN_DIR=true; }
cd "$KVM_UNIT_TEST"
[ -f "configure" ] || git clone --depth 1 -q git://git.kernel.org/pub/scm/virt/kvm/kvm-unit-tests.git .

# Compile kvm-unit-test as standalone to get tests as separate files
./configure $ENDIAN || { echo Fail to configure kvm-unit-test; exit -1; }
make standalone >/dev/null || { echo Fail to "make standalone" kvm-unit-test; exit -1; }

# Execute individual tests
cat > avocado-external-runner << \INNER_EOF
#!/bin/sh
./$*
ret=$?
[ $ret -le 1 ] && exit 0 || exit $ret
INNER_EOF
chmod +x avocado-external-runner
cd tests
eval "avocado run --external-runner ../avocado-external-runner $WILDCARD $*"
RET=$?

# Cleanup and exit
[ "$CLEAN_DIR" ] && rm -Rf "$KVM_UNIT_TEST"
exit $RET
