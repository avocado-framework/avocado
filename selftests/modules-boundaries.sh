#!/bin/bash

# number of infringements found
RESULT=0

echo -n "* Checking for avocado.core imports from examples/tests: "
LIST=`git grep -E '^(import avocado\.core.*|from avocado\.core(.*)import)' examples/tests`
COUNT=`git grep -E '^(import avocado\.core.*|from avocado\.core(.*)import)' examples/tests | wc -l`
(( RESULT = RESULT + COUNT ))
echo "$COUNT"
if [ -n "$LIST" ]; then
   echo "$LIST"
fi
unset LIST
unset COUNT

echo -n "* Checking for non-relative avocado imports from avocado/core: "
LIST=`git grep -E '^(import avocado\..*|from avocado(.*)import)' avocado/core`
COUNT=`git grep -E '^(import avocado\..*|from avocado(.*)import)' avocado/core | wc -l`
(( RESULT = RESULT + COUNT ))
echo "$COUNT"
if [ -n "$LIST" ]; then
   echo "$LIST"
fi
unset LIST
unset COUNT

echo -n "* Checking for avocado imports from avocado/utils: "
LIST=`git grep -E '^(import avocado\\.*|from avocado(.*)import)' avocado/utils`
COUNT=`git grep -E '^(import avocado\\.*|from avocado(.*)import)' avocado/utils | wc -l`
(( RESULT = RESULT + COUNT ))
echo "$COUNT"
if [ -n "$LIST" ]; then
   echo "$LIST"
fi
unset LIST
unset COUNT

if [ "$RESULT" -ne 0 ]; then
    echo "ERROR: $RESULT module boundary infringements found"
else
    echo "PASS: no module boundary infringement(s) found"
fi
exit $RESULT
