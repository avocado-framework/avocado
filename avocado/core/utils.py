import os
from uuid import uuid1

from pkg_resources import get_distribution

from ..utils import path, process
from .nrunner import Task
from .resolver import ReferenceResolutionResult
from .tags import filter_test_tags_runnable


def get_avocado_git_version():
    # if running from git sources, there will be a ".git" directory
    # 3 levels up
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    git_dir = os.path.join(base_dir, '.git')
    if not os.path.isdir(git_dir):
        return
    if not os.path.exists(os.path.join(base_dir, 'python-avocado.spec')):
        return

    try:
        git = path.find_command('git')
    except path.CmdNotFoundError:
        return

    git_dir = os.path.abspath(base_dir)
    cmd = "%s -C %s show --summary --pretty='%%H'" % (git, git_dir)
    res = process.run(cmd, ignore_status=True, verbose=False)
    if res.exit_status == 0:
        top_commit = res.stdout_text.splitlines()[0][:8]
        return " (GIT commit %s)" % top_commit


def prepend_base_path(value):
    expanded = os.path.expanduser(value)
    if not expanded.startswith(('/', '~', '.')):
        dist = get_distribution('avocado-framework')
        return os.path.join(dist.location, 'avocado', expanded)
    return expanded


def resolutions_to_tasks(resolutions, config):
    """
    Transforms resolver resolutions into tasks

    A resolver resolution
    (:class:`avocado.core.resolver.ReferenceResolution`) contains
    information about the resolution process (if it was successful
    or not) and in case of successful resolutions a list of
    resolutions.  It's expected that the resolution are
    :class:`avocado.core.nrunner.Runnable`.

    This method transforms those runnables into Tasks
    (:class:`avocado.core.nrunner.Task`), which will include a status
    reporting URI.  It also performs tag based filtering on the
    runnables for possibly excluding some of the Runnables.

    :param resolutions: possible multiple resolutions for multiple
                        references
    :type resolutions: list of :class:`avocado.core.resolver.ReferenceResolution`
    :param config: job configuration
    :type config: dict
    :returns: the resolutions converted to tasks
    :rtype: list of :class:`avocado.core.nrunner.Task`
    """

    tasks = []
    filter_by_tags = config.get("filter.by_tags.tags")
    include_empty = config.get("filter.by_tags.include_empty")
    include_empty_key = config.get('filter.by_tags.include_empty_key')
    status_server = config.get('nrunner.status_server_uri')
    for resolution in resolutions:
        if resolution.result != ReferenceResolutionResult.SUCCESS:
            continue
        for runnable in resolution.resolutions:
            if filter_by_tags:
                if not filter_test_tags_runnable(runnable,
                                                 filter_by_tags,
                                                 include_empty,
                                                 include_empty_key):
                    continue
            tasks.append(Task(str(uuid1()), runnable, [status_server]))
    return tasks
