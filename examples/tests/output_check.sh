#!/bin/sh

# if you execute this script with avocado, avocado will check its stdout
# against the file stdout.expected and its stderr with the file stderr.expected,
# both located in output_check.sh.data, in the same directory as this source
# file.

# The expected files were generated using the option --output-check-record all
# of the avocado runner:
# avocado run output_check.sh --output-check-record all

echo "Hello, world!"
