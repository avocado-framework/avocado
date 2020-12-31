#!/bin/sh -e

PARENT=$(cd ..; pwd)

isort $PARENT --check-only \
              --skip $PARENT/selftests/run \
              --skip $PARENT/selftests/unit/test_datadir.py \
              --skip $PARENT/selftests/.data/loader_instrumented/double_import.py \
              --skip $PARENT/selftests/.data/loader_instrumented/dont_detect_non_avocado.py \
              --skip $PARENT/selftests/.data/loader_instrumented/imports.py \
              --skip $PARENT/selftests/functional/test_basic.py \
              --skip $PARENT/selftests/functional/test_interrupt.py \
              --skip $PARENT/avocado/__init__.py \
              --skip $PARENT/avocado/core/main.py \
              --skip $PARENT/avocado/plugins/exec_path.py \
              --skip $PARENT/optional_plugins/resultsdb/avocado_resultsdb/__init__.py \
              --skip $PARENT/optional_plugins/varianter_yaml_to_mux/avocado_varianter_yaml_to_mux/__init__.py \
              --skip $PARENT/optional_plugins/varianter_yaml_to_mux/tests/test_functional.py \
              --skip $PARENT/optional_plugins/varianter_yaml_to_mux/tests/test_unit.py \
              --skip $PARENT/optional_plugins/html/avocado_result_html/__init__.py \
              --skip $PARENT/optional_plugins/robot/avocado_robot/runner.py \
              --skip $PARENT/optional_plugins/robot/avocado_robot/__init__.py \
              --skip $PARENT/optional_plugins/robot/tests/test_robot.py \
              --skip $PARENT/optional_plugins/varianter_cit/tests/test_basic.py \
              --quiet
