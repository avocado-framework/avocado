#!/bin/sh -e

isort --recursive --check-only \
      --skip selftests/.data/loader_instrumented/dont_crash.py \
      --skip selftests/.data/loader_instrumented/double_import.py \
      --skip selftests/.data/loader_instrumented/dont_detect_non_avocado.py \
      --skip avocado/__init__.py
