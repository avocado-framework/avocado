# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: Red Hat Inc. 2019
# Authors: Cleber Rosa <crosa@redhat.com>

"""
Test resolver for builtin test types
"""

import json
import os
import re
import shlex
import subprocess

from avocado.core.extension_manager import PluginPriority
from avocado.core.nrunner.runnable import Runnable
from avocado.core.plugin_interfaces import Init, Resolver
from avocado.core.references import reference_split
from avocado.core.resolver import (
    ReferenceResolution,
    ReferenceResolutionResult,
    check_file,
    get_file_assets,
)
from avocado.core.safeloader import find_avocado_tests, find_python_unittests
from avocado.core.settings import settings


class BaseExec:
    @staticmethod
    def check_exec(reference):
        criteria_check = check_file(
            reference,
            reference,
            suffix=None,
            type_name="executable file",
            access_check=os.R_OK | os.X_OK,
            access_name="executable",
        )
        if criteria_check is not True:
            return criteria_check


class ExecTestResolver(BaseExec, Resolver):

    name = "exec-test"
    description = "Test resolver for executable files to be handled as tests"
    priority = PluginPriority.VERY_LOW

    def resolve(self, reference):
        exec_criteria = self.check_exec(reference)
        if exec_criteria is not None:
            return exec_criteria

        runnable = Runnable("exec-test", reference, assets=get_file_assets(reference))
        return ReferenceResolution(
            reference, ReferenceResolutionResult.SUCCESS, [runnable]
        )


def python_resolver(name, reference, find_tests):
    module_path, tests_filter = reference_split(reference)
    if tests_filter is not None:
        tests_filter = re.compile(tests_filter)

    criteria_check = check_file(module_path, reference)
    if criteria_check is not True:
        return criteria_check

    # disabled tests not needed here
    class_methods_info, _ = find_tests(module_path)
    runnables = []
    for klass, methods_tags_depens in class_methods_info.items():
        for method, tags, depens in methods_tags_depens:
            klass_method = f"{klass}.{method}"
            if tests_filter is not None and not tests_filter.search(klass_method):
                continue
            uri = f"{module_path}:{klass_method}"
            runnables.append(
                Runnable(
                    name,
                    uri=uri,
                    tags=tags,
                    dependencies=depens,
                    assets=get_file_assets(module_path),
                )
            )
    if runnables:
        return ReferenceResolution(
            reference, ReferenceResolutionResult.SUCCESS, runnables
        )

    return ReferenceResolution(reference, ReferenceResolutionResult.NOTFOUND)


class PythonUnittestResolver(Resolver):

    name = "python-unittest"
    description = "Test resolver for Python Unittests"

    @staticmethod
    def _find_compat(module_path):
        """Used as compatibility for the :func:`python_resolver()` interface."""
        return find_python_unittests(module_path), None

    def resolve(self, reference):
        return python_resolver(
            PythonUnittestResolver.name, reference, PythonUnittestResolver._find_compat
        )


class AvocadoInstrumentedResolver(Resolver):

    name = "avocado-instrumented"
    description = "Test resolver for Avocado Instrumented tests"
    priority = PluginPriority.HIGH

    def resolve(self, reference):
        return python_resolver(
            AvocadoInstrumentedResolver.name, reference, find_avocado_tests
        )


class TapResolver(BaseExec, Resolver):

    name = "tap"
    description = "Test resolver for executable files to be handled as TAP tests"
    priority = PluginPriority.LAST_RESORT

    def resolve(self, reference):
        exec_criteria = self.check_exec(reference)
        if exec_criteria is not None:
            return exec_criteria

        runnable = Runnable("tap", reference, assets=get_file_assets(reference))
        return ReferenceResolution(
            reference, ReferenceResolutionResult.SUCCESS, [runnable]
        )


class RunnableRecipeResolver(Resolver):
    name = "runnable-recipe"
    description = "Test resolver for JSON runnable recipes"

    def resolve(self, reference):
        criteria_check = check_file(
            reference, reference, suffix=".json", type_name="JSON file"
        )
        if criteria_check is not True:
            return criteria_check

        runnable = Runnable.from_recipe(reference)
        return ReferenceResolution(
            reference, ReferenceResolutionResult.SUCCESS, [runnable]
        )


class RunnablesRecipeResolver(Resolver):
    name = "runnables-recipe"
    description = "Test resolver for multiple runnables in a JSON recipe file"

    @staticmethod
    def _validate_and_load_runnables(reference):
        with open(reference, "r", encoding="utf-8") as json_file:
            runnables = json.load(json_file)

        if not (
            isinstance(runnables, list)
            and all([isinstance(r, dict) for r in runnables])
        ):
            return ReferenceResolution(
                reference,
                ReferenceResolutionResult.NOTFOUND,
                info="File {reference} does not look like a runnables recipe JSON file",
            )

        return ReferenceResolution(
            reference,
            ReferenceResolutionResult.SUCCESS,
            [Runnable.from_dict(r) for r in runnables],
        )

    def resolve(self, reference):
        criteria_check = check_file(
            reference, reference, suffix=".json", type_name="JSON file"
        )
        if criteria_check is not True:
            return criteria_check

        return self._validate_and_load_runnables(reference)


class ExecRunnablesRecipeInit(Init):
    name = "exec-runnables-recipe"
    description = 'Configuration for resolver plugin "exec-runnables-recipe" plugin'

    def initialize(self):
        help_msg = (
            'Whether resolvers (such as "exec-runnables-recipe") should '
            "execute files given as test references that have executable "
            "permissions. This is disabled by default due to security "
            "implications of running executables that may not be trusted."
        )
        settings.register_option(
            section="resolver",
            key="run_executables",
            key_type=bool,
            default=False,
            help_msg=help_msg,
        )

        help_msg = (
            "Command line options (space separated) that will be added "
            "to the executable when executing it as a producer of "
            "runnables-recipe JSON content."
        )
        settings.register_option(
            section="resolver.exec_runnables_recipe",
            key="arguments",
            key_type=str,
            default="",
            help_msg=help_msg,
        )


class ExecRunnablesRecipeResolver(BaseExec, Resolver):
    name = "exec-runnables-recipe"
    description = "Test resolver for executables that output JSON runnable recipes"
    priority = PluginPriority.LOW

    def resolve(self, reference):
        if not self.config.get("resolver.run_executables"):
            return ReferenceResolution(
                reference,
                ReferenceResolutionResult.NOTFOUND,
                info=(
                    "Running executables is not enabled. Refer to "
                    '"resolver.run_executables" configuration option'
                ),
            )

        exec_criteria = self.check_exec(reference)
        if exec_criteria is not None:
            return exec_criteria

        args = self.config.get("resolver.exec_runnables_recipe.arguments")
        if args:
            cmd = [reference] + shlex.split(args)
        else:
            cmd = reference
        try:
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except (FileNotFoundError, PermissionError) as exc:
            return ReferenceResolution(
                reference,
                ReferenceResolutionResult.NOTFOUND,
                info=(f'Failure while running running executable "{reference}": {exc}'),
            )

        content, _ = process.communicate()
        try:
            runnables = json.loads(content)
        except json.JSONDecodeError:
            return ReferenceResolution(
                reference,
                ReferenceResolutionResult.NOTFOUND,
                info=f'Content generated by running executable "{reference}" is not JSON',
            )

        if not (
            isinstance(runnables, list)
            and all([isinstance(r, dict) for r in runnables])
        ):
            return ReferenceResolution(
                reference,
                ReferenceResolutionResult.NOTFOUND,
                info=f"Content generated by running executable {reference} does not look like a runnables recipe JSON content",
            )

        return ReferenceResolution(
            reference,
            ReferenceResolutionResult.SUCCESS,
            [Runnable.from_dict(r) for r in runnables],
        )
