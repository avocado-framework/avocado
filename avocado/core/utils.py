import os

from pkg_resources import get_distribution

from ..utils import path, process


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
