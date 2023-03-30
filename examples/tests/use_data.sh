#!/bin/sh -e
# A minimal test that depends on the presence of data files
test -f "$(dirname $0)/$(basename $0).data/data"
