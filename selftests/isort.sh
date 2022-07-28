#!/bin/sh -e

isort --check-only --profile black \
      --skip selftests/.data/safeloader/data/double_import.py \
      --skip selftests/.data/safeloader/data/dont_detect_non_avocado.py \
      --skip selftests/.data/safeloader/data/imports.py \
      --skip avocado/__init__.py .
