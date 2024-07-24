#!/bin/sh -e
echo "** Running spell check..."

python3 -m pylint -j 1 --disable=all --enable=spelling --spelling-dict=en_US --spelling-private-dict-file=spell.ignore *
