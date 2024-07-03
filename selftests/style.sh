#!/bin/sh -e
echo "** Running black..."

python3 -m black --check --diff --color .
