#!/bin/sh -e

PARENT=$(cd ..; pwd)

isort $PARENT --check-only --quiet
