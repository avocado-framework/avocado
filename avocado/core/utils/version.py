import os

from avocado.utils import path, process


def get_avocado_git_version():
    # if running from git sources, there will be a ".git" directory
    # 4 levels up
    dn = os.path.dirname
    base_dir = dn(dn(dn(dn(__file__))))
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
    cmd = f"{git} -C {git_dir} show --summary --pretty='%H'"
    res = process.run(cmd, ignore_status=True, verbose=False)
    if res.exit_status == 0:
        top_commit = res.stdout_text.splitlines()[0][:8]
        return f" (GIT commit {top_commit})"
