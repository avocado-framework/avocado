#!/bin/sh
kind=${1:-exec-test}
echo "[{\"kind\": \"$kind\",\"uri\": \"/bin/true\",\"identifier\": \"true-test\"},{\"kind\": \"$kind\",\"uri\": \"/bin/false\",\"identifier\": \"false-test\"}]"
