#!/bin/bash -e

echo "** Running signedoff-check..."
if [ -z "$COMMIT_COUNT" ]; then
  COMMIT_COUNT=1
fi
readarray -t commits <<< $(git log --no-merges -n "$COMMIT_COUNT" --format='%H')
for commit in "${commits[@]}"; do
  AUTHOR=$(git log -1 --format='%aN <%aE>' "$commit")
  HEADER=$(git log -1 --format='%s' "$commit")
  echo " Checking commit with header: '$HEADER"
  if ! git log -1 --pretty=format:%B "$commit" | grep -i "Signed-off-by: $AUTHOR"; then
    echo "The commit message does not contain author's signature (Signed-off-by: $AUTHOR)"
    exit 1
  fi
done
