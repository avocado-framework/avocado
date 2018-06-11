#!/bin/sh
# This test demonstrates that shell scripts have access to avocado runtime
# information, exported through environment variables.
echo "Avocado Version: $AVOCADO_VERSION"
echo "Avocado Test basedir: $AVOCADO_TEST_BASEDIR"
echo "Avocado Test datadir: $AVOCADO_TEST_DATADIR"
echo "Avocado Test workdir: $AVOCADO_TEST_WORKDIR"
echo "Avocado Test logdir: $AVOCADO_TEST_LOGDIR"
echo "Avocado Test logfile: $AVOCADO_TEST_LOGFILE"
echo "Avocado Test outputdir: $AVOCADO_TEST_OUTPUTDIR"
echo "Custom variable: $CUSTOM_VARIABLE"

test -d "$AVOCADO_TEST_BASEDIR" -a \
     -d "$AVOCADO_TEST_WORKDIR" -a \
     -d "$AVOCADO_TEST_LOGDIR" -a \
     -f "$AVOCADO_TEST_LOGFILE" -a \
     -d "$AVOCADO_TEST_OUTPUTDIR"
