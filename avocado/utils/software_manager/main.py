import argparse
import logging

from .. import exit_codes
from .manager import SoftwareManager

log = logging.getLogger('avocado.utils.software_manager')

MESSAGES = {
    'install': {
        'success': 'Package(s) %s installed successfully',
        'fail': 'Failed to install %s. Check the package(s) name and if sudo'
        ' permission is granted.'
    },
    'remove': {
        'success': 'Package(s) %s removed successfully',
        'fail': 'Failed to remove %s. Check the package(s) name and if sudo'
        ' permission is granted.'
    },
    'check-installed': {
        'success': 'Package %s already installed',
        'fail': 'Package %s not installed'
    },
    'add-repo': {
        'success': 'Repo %s added successfully',
        'fail': 'Failed add repo %s. Check the repo name and if sudo'
        ' permission is granted.'
    },
    'remove-repo': {
        'success': 'Repo %s removed successfully',
        'fail': 'Failed to remove repo %s. Check the repo name and if sudo'
        ' permission is granted.'
    },
    'upgrade': 'Package manager upgrade successful',
    'what-provides': 'Package %s provides %s',
    'install-what-provides': 'Installed successfully what provides %s',
}


def main():
    exitcode = exit_codes.UTILITY_OK
    parser = argparse.ArgumentParser(
        "install|remove|check-installed|list-all|list-files|add-repo|"
        "remove-repo|upgrade|what-provides|install-what-provides arguments")
    parser.add_argument('--verbose', dest="debug", action='store_true',
                        help='include debug messages in console output')

    namespace, args = parser.parse_known_args()

    if namespace.debug:
        logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    else:
        logging.basicConfig(level=logging.INFO, format='%(message)s')

    software_manager = SoftwareManager()
    if args:
        action = args[0]
        args = " ".join(args[1:])
    else:
        action = 'show-help'

    if action == 'install':
        if software_manager.install(args):
            log.info(MESSAGES[action]['success'], args)
        else:
            log.error(MESSAGES[action]['fail'], args)
            exitcode = exit_codes.UTILITY_FAIL

    elif action == 'remove':
        if software_manager.remove(args):
            log.info(MESSAGES[action]['success'], args)
        else:
            log.error(MESSAGES[action]['fail'], args)
            exitcode = exit_codes.UTILITY_FAIL

    elif action == 'check-installed':
        if software_manager.check_installed(args):
            log.info(MESSAGES[action]['success'], args)
        else:
            log.info(MESSAGES[action]['fail'], args)
            exitcode = exit_codes.UTILITY_FAIL

    elif action == 'list-all':
        for pkg in software_manager.list_all():
            log.info(pkg)

    elif action == 'list-files':
        for f in software_manager.list_files(args):
            log.info(f)

    elif action == 'add-repo':
        if software_manager.add_repo(args):
            log.info(MESSAGES[action]['success'], args)
        else:
            log.error(MESSAGES[action]['fail'], args)
            exitcode = exit_codes.UTILITY_FAIL

    elif action == 'remove-repo':
        if software_manager.remove_repo(args):
            log.info(MESSAGES[action]['success'], args)
        else:
            log.error(MESSAGES[action]['fail'], args)
            exitcode = exit_codes.UTILITY_FAIL

    elif action == 'upgrade':
        if software_manager.upgrade():
            log.info(MESSAGES[action])

    elif action == 'what-provides':
        provides = software_manager.provides(args)
        if provides is not None:
            log.info(MESSAGES[action], provides, args)

    elif action == 'install-what-provides':
        if software_manager.install_what_provides(args):
            log.info(MESSAGES[action], args)

    elif action == 'show-help':
        parser.print_help()

    return exitcode
