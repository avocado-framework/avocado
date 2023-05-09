#!/bin/sh
# This test demonstrates that shell scripts have access to avocado runtime
# information, exported through environment variables.
echo "Avocado Version: $AVOCADO_VERSION"
echo "Avocado Test basedir: $AVOCADO_TEST_BASEDIR"
test -d "$AVOCADO_TEST_BASEDIR" || exit 1
echo "Avocado Test workdir: $AVOCADO_TEST_WORKDIR"
test -d "$AVOCADO_TEST_WORKDIR" || exit 1
echo "Avocado Test logdir: $AVOCADO_TEST_LOGDIR"
test -d "$AVOCADO_TEST_LOGDIR" || exit 1
echo "Avocado Test logfile: $AVOCADO_TEST_LOGFILE"
test -f "$AVOCADO_TEST_LOGFILE" || exit 1
echo "Avocado Test outputdir: $AVOCADO_TEST_OUTPUTDIR"
test -d "$AVOCADO_TEST_OUTPUTDIR" || exit 1
echo "Custom variable: $CUSTOM_VARIABLE"
