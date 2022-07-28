#!/bin/sh -e
echo "** Running black..."

black --check --diff --color .
