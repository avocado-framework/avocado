#!/bin/sh -e
echo "** Running lint..."

PYLINT=$(which pylint 2>/dev/null || python3 -m pylint)

# Those are files from our main packages, we should follow the .pylintrc file with all
# enabled by default. Some are disabled, we are working to reduce this list.
FILES=$(git ls-files '*.py')
${PYLINT} ${PYLINT_OPTIONS} ${FILES}
