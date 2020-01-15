#!/bin/sh -e

if [ -z "$AVOCADO_WORK_DIR" ]; then
    exit 1
fi

if ! [ -d "$AVOCADO_WORK_DIR" ]; then
    exit 1
fi

OUTPUT_FILE="$AVOCADO_WORK_DIR/avocado-examples-nrunner-tests-creates-file-in-work-dir"
echo "OUTPUT_FILE: $OUTPUT_FILE"
echo 'THIS_FILE_SHOULD_BE_REMOVED_AUTOMATICALLY' > $OUTPUT_FILE
