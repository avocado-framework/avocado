#!/bin/sh -e

echo "** Running signedoff-check..."

AUTHOR="$(git log --no-merges -1 --pretty='format:%aN <%aE>')"
git log --no-merges -1 --pretty=format:%B | grep -i "Signed-off-by: $AUTHOR"
if [ $? != 0 ]; then
    echo "The commit message does not contain author's signature (Signed-off-by: $AUTHOR)"
    exit 1
fi
