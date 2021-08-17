#!/bin/sh
if [[ -z ${SLEEP_LENGTH} ]]; then
  SLEEP_LENGTH=1
fi

echo "Sleeping $SLEEP_LENGTH"
sleep $SLEEP_LENGTH
