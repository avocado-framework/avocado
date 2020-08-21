import argparse
import logging

from .manager import SoftwareManager

log = logging.getLogger('avocado.utils.software_manager')


def main():
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
            log.info("Packages %s installed successfully", args)
        else:
            log.error("Failed to install %s", args)

    elif action == 'remove':
        if software_manager.remove(args):
            log.info("Packages %s removed successfully", args)
        else:
            log.error("Failed to remove %s", args)

    elif action == 'check-installed':
        if software_manager.check_installed(args):
            log.info("Package %s already installed", args)
        else:
            log.info("Package %s not installed", args)

    elif action == 'list-all':
        for pkg in software_manager.list_all():
            log.info(pkg)

    elif action == 'list-files':
        for f in software_manager.list_files(args):
            log.info(f)

    elif action == 'add-repo':
        if software_manager.add_repo(args):
            log.info("Repo %s added successfully", args)
        else:
            log.error("Failed to remove repo %s", args)

    elif action == 'remove-repo':
        if software_manager.remove_repo(args):
            log.info("Repo %s removed successfully", args)
        else:
            log.error("Failed to remove repo %s", args)

    elif action == 'upgrade':
        if software_manager.upgrade():
            log.info("Package manager upgrade successful")

    elif action == 'what-provides':
        provides = software_manager.provides(args)
        if provides is not None:
            log.info("Package %s provides %s", provides, args)

    elif action == 'install-what-provides':
        if software_manager.install_what_provides(args):
            log.info("Installed successfully what provides %s", args)

    elif action == 'show-help':
        parser.print_help()
