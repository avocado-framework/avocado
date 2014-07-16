"""
selinux test utility functions.
"""

import logging
import re
import os.path
from autotest.client import utils


class SelinuxError(Exception):

    """
    Error selinux utility functions.
    """
    pass


class SeCmdError(SelinuxError):

    """
    Error in executing cmd.
    """

    def __init__(self, cmd, detail):
        SelinuxError.__init__(self)
        self.cmd = cmd
        self.detail = detail

    def __str__(self):
        return str("Execute command %s failed.\n"
                   "Detail: %s .\n" % (self.cmd, self.detail))


class SemanageError(SelinuxError):

    """
    Error when semanage binary is not found
    """

    def __str__(self):
        return ("The semanage command is not available, "
                "please install policycoreutils "
                "or equivalent for your platform.")


class RestoreconError(SelinuxError):

    def __str__(self):
        return ("Output from the restorecon command"
                "does not match the expected format")

STATUS_LIST = ['enforcing', 'permissive', 'disabled']


def get_status():
    """
    Get the status of selinux.

    :return: string of status in STATUS_LIST.
    :raise SeCmdError: if execute 'getenforce' failed.
    :raise SelinuxError: if 'getenforce' command exit 0,
                    but the output is not expected.
    """
    cmd = 'getenforce'
    result = utils.run(cmd, ignore_status=True)
    if result.exit_status:
        raise SeCmdError(cmd, result.stderr)

    for status in STATUS_LIST:
        if result.stdout.lower().count(status):
            return status
        else:
            continue

    raise SelinuxError("result of 'getenforce' (%s)is not expected."
                       % result.stdout)


def set_status(status):
    """
    Set status of selinux.

    :param status: status want to set selinux.
    :raise SelinuxError: status is not supported.
    :raise SelinuxError: need to reboot host.
    :raise SeCmdError: execute setenforce failed.
    :raise SelinuxError: cmd setenforce exit normally,
                but status of selinux is not set to expected.
    """
    if status not in STATUS_LIST:
        raise SelinuxError("Status %s is not accepted." % status)

    current_status = get_status()
    if status == current_status:
        return
    else:
        if current_status == "disabled" or status == "disabled":
            raise SelinuxError("Please modify /etc/selinux/config and "
                               "reboot host to set selinux to %s." % status)
        else:
            cmd = "setenforce %s" % status
            result = utils.run(cmd, ignore_status=True)
            if result.exit_status:
                raise SeCmdError(cmd, result.stderr)
            else:
                current_status = get_status()
                if not status == current_status:
                    raise SelinuxError("Status of selinux is set to %s,"
                                       "but not expected %s. "
                                       % (current_status, status))
                else:
                    pass

    logging.debug("Set status of selinux to %s success.", status)


def is_disabled():
    """
    Return True if the selinux is disabled.
    """
    status = get_status()
    if status == "disabled":
        return True
    else:
        return False


def is_not_disabled():
    """
    Return True if the selinux is not disabled.
    """
    return not is_disabled()


def is_enforcing():
    """
    Return true if the selinux is enforcing.
    """
    return (get_status() == "enforcing")


def is_permissive():
    """
    Return true if the selinux is permissive.
    """
    return (get_status() == "permissive")


def get_context_from_str(context):
    """
    Get the context in a context.

    :param context: SELinux context string
    :raise SelinuxError: if there is no context in context.
    """
    context_pattern = (r"[a-z,_]*_u:[a-z,_]*_r:[a-z,_]*_t"
                       # non-greedy/non-group match on optional MLS range
                       r"(?:\:[s,\-,0-9,:[c,\,,0-9]*]*)?")
    if re.search(context_pattern, context):
        context_list = re.findall(context_pattern, context)
        return context_list[0]

    raise SelinuxError("There is no context in %s." % context)


def get_type_from_context(context):
    """
    Return just the type component of a full context string

    :param context: SELinux context string
    :return: Type component of SELinux context string
    """
    # Raise exception if not a context string
    get_context_from_str(context)
    type_pattern = (r"[a-z,_]*_u:[a-z,_]*_r:([a-z,_]*_t)"
                    r"(?:\:[s,\-,0-9,:[c,\,,0-9]*]*)?")
    return re.search(type_pattern, context).group(1)


def get_context_of_file(filename):
    """
    Get the context of file.

    :raise SeCmdError: if execute 'getfattr' failed.
    """
    # More direct than scraping 'ls' output.
    cmd = "getfattr --name security.selinux %s" % filename
    result = utils.run(cmd, ignore_status=True)
    if result.exit_status:
        raise SeCmdError(cmd, result.stderr)

    output = result.stdout
    return get_context_from_str(output)


def set_context_of_file(filename, context):
    """
    Set context of file.

    :raise SeCmdError: if failed to execute chcon.
    :raise SelinuxError: if command chcon execute
                        normally, but the context of
                        file is not setted to context.
    """
    context = context.strip()
    # setfattr used for consistency with getfattr use above
    cmd = ("setfattr --name security.selinux --value \"%s\" %s"
           % (context, filename))
    result = utils.run(cmd, ignore_status=True)
    if result.exit_status:
        raise SeCmdError(cmd, result.stderr)

    context_result = get_context_of_file(filename)
    if not context == context_result:
        raise SelinuxError("Context of %s after chcon is %s, "
                           "but not expected %s."
                           % (filename, context_result, context))

    logging.debug("Set context of %s success.", filename)


def get_context_of_process(pid):
    """
    Get context of process.
    """
    attr_filepath = "/proc/%s/attr/current" % pid

    attr_file = open(attr_filepath)

    output = attr_file.read()
    return get_context_from_str(output)

# Force uniform handling if semanage not found (used in unittests)


def _no_semanage(cmdresult):
    if cmdresult.exit_status == 127:
        if cmdresult.stdout.lower().count('command not found'):
            raise SemanageError()


def get_defcon(local=False):
    """
    Return list of dictionaries containing SELinux default file context types

    :param local: Only return locally modified default contexts
    :return: list of dictionaries of default context attributes
    """
    if local:
        result = utils.run("semanage fcontext --list -C", ignore_status=True)
    else:
        result = utils.run("semanage fcontext --list", ignore_status=True)
    _no_semanage(result)
    if result.exit_status != 0:
        raise SeCmdError('semanage', result.stderr)
    result_list = result.stdout.strip().split('\n')
    # Need to process top-down instead of bottom-up
    result_list.reverse()
    first_line = result_list.pop()
    # First column name has a space in it
    column_names = [name.strip().lower().replace(' ', '_')
                    for name in first_line.split('  ')
                    if len(name) > 0]
    # Shorten first column name
    column_names[0] = column_names[0].replace("selinux_", "")
    fcontexts = []
    for line in result_list:
        if len(line) < 1:  # skip blank lines
            continue
        column_data = [name.strip()
                       for name in line.split('  ')
                       if len(name) > 0]
        # Enumerating data raises exception if no column_names match
        fcontext = dict([(column_names[idx], data)
                         for idx, data in enumerate(column_data)])
        # find/set functions only accept type, not full context string
        fcontext['context'] = get_type_from_context(fcontext['context'])
        fcontexts.append(fcontext)
    return fcontexts


def find_defcon_idx(defcon, pathname):
    """
    Returns the index into defcon where pathname matches or None
    """
    # Default context path regexes only work on canonical paths
    pathname = os.path.realpath(pathname)
    for default_context in defcon:
        if bool(re.search(default_context['fcontext'], pathname)):
            return defcon.index(default_context)
    return None


def find_defcon(defcon, pathname):
    """
    Returns the context type of first match to pathname or None
    """
    # Default context path regexes only work on canonical paths
    pathname = os.path.realpath(pathname)
    idx = find_defcon_idx(defcon, pathname)
    if idx is not None:
        return get_type_from_context(defcon[idx]['context'])
    else:
        return None


def find_pathregex(defcon, pathname):
    """
    Returns the regular expression in defcon matching pathname
    """
    # Default context path regexes only work on canonical paths
    pathname = os.path.realpath(pathname)
    idx = find_defcon_idx(defcon, pathname)
    if idx is not None:
        return defcon[idx]['fcontext']
    else:
        return None


def set_defcon(context_type, pathregex):
    """
    Set the default context of a file/path in local SELinux policy

    :param context_type: The selinux context (only type is used)
    :param pathregex: Pathname regex e.g. r"/foo/bar/baz(/.*)?"
    :raise SelinuxError: if semanage command not found
    :raise SeCmdError: if semanage exits non-zero
    """
    cmd = ("semanage fcontext --add -t %s '%s'" % (context_type, pathregex))
    result = utils.run(cmd, ignore_status=True)
    _no_semanage(result)
    if result.exit_status != 0:
        raise SeCmdError(cmd, result.stderr)


def del_defcon(context_type, pathregex):
    """
    Remove the default local SELinux policy type for a file/path

    :param context: The selinux context (only type is used)
    :pramm pathregex: Pathname regex e.g. r"/foo/bar/baz(/.*)?"
    :raise SelinuxError: if semanage command not found
    :raise SeCmdError: if semanage exits non-zero
    """
    cmd = ("semanage fcontext --delete -t %s '%s'" % (context_type, pathregex))
    result = utils.run(cmd, ignore_status=True)
    _no_semanage(result)
    if result.exit_status != 0:
        raise SeCmdError(cmd, result.stderr)

# Process pathname/dirdesc in uniform way for all defcon functions + unittests


def _run_restorecon(pathname, dirdesc, readonly=True):
    cmd = 'restorecon -v'
    if dirdesc:
        cmd += 'R'
    if readonly:
        cmd += 'n'
    cmd += ' "%s"' % pathname
    # Always returns 0, even if contexts wrong
    return utils.run(cmd).stdout.strip()


def verify_defcon(pathname, dirdesc=False):
    """
    Verify contexts of pathspec (and/or below, if dirdesc) match default

    :param pathname: Absolute path to file, directory, or symlink
    :param dirdesc: True to descend into sub-directories
    :return: True if all components match default contexts
    :note: By default DOES NOT follow symlinks
    """
    # Default context path regexes only work on canonical paths
    changes = _run_restorecon(pathname, dirdesc)
    if changes.count('restorecon reset'):
        return False
    else:
        return True


# Provide uniform formatting for diff and apply functions

def _format_changes(changes):
    result = []
    if changes:  # Empty string or None - return empty list
        # Could be many changes, need efficient line searching
        regex = re.compile('^restorecon reset (.+) context (.+)->(.+)')
        for change_line in changes.split('\n'):
            mobj = regex.search(change_line)
            if mobj is None:
                raise RestoreconError()
            pathname = mobj.group(1)
            from_con = mobj.group(2)
            to_con = mobj.group(3)
            result.append((pathname, from_con, to_con))
    return result


def diff_defcon(pathname, dirdesc=False):
    """
    Return a list of tuple(pathname, from, to) for current & default contexts

    :param pathname: Absolute path to file, directory, or symlink
    :param dirdesc: True to descend into sub-directories
    :return: List of tuple(pathname, from context, to context)
    """
    return _format_changes(_run_restorecon(pathname, dirdesc))


def apply_defcon(pathname, dirdesc=False):
    """
    Apply default contexts to pathname, possibly descending into sub-dirs also.

    :param pathname: Absolute path to file, directory, or symlink
    :param dirdesc: True to descend into sub-directories
    :return: List of changes applied tuple(pathname, from context, to context)
    """
    return _format_changes(_run_restorecon(pathname, dirdesc, readonly=False))


def transmogrify_usr_local(pathregex):
    """
    Replace usr/local/something with usr/(local/)?something
    """
    # Whoa! don't mess with short path regex's
    if len(pathregex) < 3:
        return pathregex
    if pathregex.count('usr/local'):
        pathregex = pathregex.replace('usr/local/', r'usr/(local/)?')
    return pathregex


def transmogrify_sub_dirs(pathregex):
    """
    Append '(/.*)?' regex to end of pathregex to optionally match all subdirs
    """
    # Whoa! don't mess with short path regex's
    if len(pathregex) < 3:
        return pathregex
    # Doesn't work with path having trailing slash
    if pathregex.endswith('/'):
        pathregex = pathregex[0:-1]
    return pathregex + r'(/.*)?'
