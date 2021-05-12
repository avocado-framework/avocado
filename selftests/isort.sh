#!/bin/sh -e

isort --check-only \
      --skip selftests/.data/loader_instrumented/dont_crash.py \
      --skip selftests/.data/loader_instrumented/double_import.py \
      --skip selftests/.data/loader_instrumented/dont_detect_non_avocado.py \
      --skip selftests/.data/loader_instrumented/imports.py \
      --skip avocado/__init__.py .
