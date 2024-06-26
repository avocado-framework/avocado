#!/bin/sh -e
echo "** Running lint..."

# Those are files from our main packages, we should follow the .pylintrc file with all
# enabled by default. Some are disabled, we are working to reduce this list.
FILES=$(git ls-files '*.py')
python3 -m pylint ${PYLINT_OPTIONS} ${FILES}
