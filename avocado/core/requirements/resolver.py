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
# Copyright: Red Hat Inc. 2020
# Authors: Willian Rampazzo <willianr@redhat.com>

"""
Requirements Resolver module.
"""

import asyncio

from ..nrunner import Runnable, Task, RUNNERS_REGISTRY_PYTHON_CLASS
from ..task.runtime import RuntimeTask

SUPPORTED_REQUIREMENTS = {}


async def check_task_requirements(spawner, runtime_task):
    """Entry point for the Requirements Resolver.

    This function isolates the Requirements Resolver object into this module.

    :param spawner:
    :param type: :class:`avocado.plugins.spawner`
    :param runtime_task:
    :param type: :class:`avocado.core.task.runtime.RuntimeTask`
    """

    if runtime_task.task.runnable.requirements is None:
        return True

    resolver = RequirementsResolver(spawner,
                                    runtime_task.task.runnable.requirements)
    return await resolver.check_task_requirements()

class UnsupportedRequirementType(Exception):
    pass

class RequirementsResolver:
    """

    """

    def __init__(self, spawner, requirements):
        """

        """
        self._spawner = spawner
        self._requirements = requirements

    async def check_task_requirements(self):
        """

        """
        print("Requirements: %s" % self._requirements)

        for requirement in self._requirements:
            try:
                type_klass = SUPPORTED_REQUIREMENTS[requirement['type']]
            except KeyError:
                # ignore while in draft
                continue
                #raise UnsupportedRequirementType

            fulfiller = type_klass(self._spawner, requirement)
            await fulfiller.fulfill()
        return True

class BaseRequirement:
    """Base interface for a requirement type."""

    def __init__(self, spawner, requirement):
        """

        """
        self._spawner = spawner
        self._requirement = requirement

    def fulfill(self):
        """

        """
        raise NotImplementedError

class PackageRequirement(BaseRequirement):
    """

    """

    async def fulfill(self):
        """

        """
        print('Fulfilling: %s' % self._requirement)
        # change the argument to 'install' after draft
        runnable = Runnable('exec', 'avocado-software-manager', 'check-installed',
                            self._requirement['name'])
        # decide how to handle ids and logs
        task_id = 'requirement-%s' % self._requirement['name']
        task = Task(task_id, runnable,
                    known_runners=RUNNERS_REGISTRY_PYTHON_CLASS)
        runtime_task = RuntimeTask(task)

        # this is a subset without error handling of the task state machine
        start_ok = await self._spawner.spawn_task(runtime_task)
        if not start_ok:
            return False
        await asyncio.wait_for(self._spawner.wait_task(runtime_task), timeout=30)

        return True

SUPPORTED_REQUIREMENTS['package'] = PackageRequirement
