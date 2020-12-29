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

from ..nrunner import RUNNERS_REGISTRY_PYTHON_CLASS, Runnable, Task

SUPPORTED_REQUIREMENTS = {}


def create_requirements_tasks(tasks):
    """Entry point for the Requirements Resolver.

    This function isolates the Requirements Resolver object into this module.

    :param tasks: List of tasks
    :type tasks: list
    """
    resolver = RequirementsResolver(tasks)
    return resolver.create_requirements_tasks()


class UnsupportedRequirementType(Exception):
    pass


class RequirementsResolver:
    """Requirements Resolver class."""

    def __init__(self, tasks):
        """
        :param tasks: List of tasks to be resolved
        :type tasks: list
        """
        self._tasks = tasks

    def create_requirements_tasks(self):
        """Create the list of tasks based on the test requirements."""
        requirements_tasks = []
        for task in self._tasks:
            if not task.runnable.requirements:
                continue

            uris = [status_service.uri
                    for status_service in task.status_services]

            for requirement in task.runnable.requirements:
                try:
                    type_klass = SUPPORTED_REQUIREMENTS[requirement['type']]
                except KeyError:
                    raise UnsupportedRequirementType

                type_resolver = type_klass(requirement, uris)
                # create the new task based on requirement information
                requirement_task = type_resolver.task_from_requirement()
                # add the new task to the requirements tasks list
                requirements_tasks.append(requirement_task)
                # update the dependency list of the father task
                task.prereqs.append(requirement_task.uid)
        # update the tasks list with the new requirements tasks
        self._tasks.extend(requirements_tasks)
        return self._tasks


class BaseRequirement:
    """Base interface for a requirement type."""

    def __init__(self, requirement, uris):
        self._requirement = requirement
        self._uris = uris

    def task_from_requirement(self):
        raise NotImplementedError


class PackageRequirement(BaseRequirement):
    """Handle requirements of type `package`."""

    def task_from_requirement(self):
        """Create a new software-manager task from the requirement info."""
        # create a software-manager runnable
        runnable = Runnable('requirement', 'avocado-software-manager',
                            'install',
                            self._requirement['name'])
        task_id = 'requirement-%s-%s' % (self._requirement['type'],
                                         self._requirement['name'])
        # create the new software-manager task for the requirement
        task = Task(task_id, runnable,
                    status_uris=self._uris,
                    known_runners=RUNNERS_REGISTRY_PYTHON_CLASS)
        return task

SUPPORTED_REQUIREMENTS['package'] = PackageRequirement
