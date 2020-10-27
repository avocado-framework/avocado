#!/bin/bash 

fail=0
for file in ../examples/doc/*.sh
do
  bash "$file" > /dev/null 2>&1
  exit_code=$?
  directory=$(dirname $file) 
  file=$(basename $file)
  code=$(cut -c-1 "$directory/.${file::-3}")
  if [ $exit_code -ne $code ]; then
      echo "The test $file failed"
      fail=1
  fi
done
exit $fail

