#!/bin/sh -e
# Script to keep the references to a home dir (in docs) without specific names
git grep /home/ -- docs/source/ man/ | cut -d ':' -f 1 | sort -u | xargs sed -i -E 's/\/home\/[a-z]+\//\/home\/user\//'
