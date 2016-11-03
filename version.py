import subprocess

# Get the current commit.
cmd = 'git log -1 --format=%H'
_current_commit = subprocess.check_output(cmd.split())

# Check the current commit tag.
cmd = 'git tag -l --points-at %s' % _current_commit
_tag = subprocess.check_output(cmd.split())

if _tag:
    if len(_tag.splitlines()) > 1:
        raise EnvironmentError('More than one tag in the current commit.')
    VERSION = _tag.strip()
else:
    VERSION = 'git%s.0' % _current_commit[:7]
