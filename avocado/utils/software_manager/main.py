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
# Copyright: IBM 2008-2009
# Copyright: Red Hat Inc. 2009-2014
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>
# Author: Higor Vieira Alves <halves@br.ibm.com>
# Author: Ramon de Carvalho Valle <rcvalle@br.ibm.com>

#
# This code was adapted from the autotest project,
# client/shared/software_manager.py


"""
Software package management library.

This is an abstraction layer on top of the existing distributions high level
package managers. It supports package operations useful for testing purposes,
and multiple high level package managers (here called backends).
"""

import argparse
import logging

from avocado.utils import exit_codes
from avocado.utils.software_manager.manager import SoftwareManager

log = logging.getLogger("avocado.utils.software_manager")

MESSAGES = {
    "install": {
        "success": "Package(s) %s installed successfully",
        "fail": "Failed to install %s. Check the package(s) name and if sudo"
        " permission is granted.",
    },
    "remove": {
        "success": "Package(s) %s removed successfully",
        "fail": "Failed to remove %s. Check the package(s) name and if sudo"
        " permission is granted.",
    },
    "check-installed": {
        "success": "Package %s already installed",
        "fail": "Package %s not installed",
    },
    "add-repo": {
        "success": "Repo %s added successfully",
        "fail": "Failed add repo %s. Check the repo name and if sudo"
        " permission is granted.",
    },
    "remove-repo": {
        "success": "Repo %s removed successfully",
        "fail": "Failed to remove repo %s. Check the repo name and if sudo"
        " permission is granted.",
    },
    "upgrade": "Package manager upgrade successful",
    "what-provides": "Package %s provides %s",
    "install-what-provides": "Installed successfully what provides %s",
}


# pylint: disable=R0914
def main():
    def install():
        if software_manager.install(args):
            log.info(MESSAGES[action]["success"], args)
            return exit_codes.UTILITY_OK
        log.error(MESSAGES[action]["fail"], args)
        return exit_codes.UTILITY_FAIL

    def remove():
        if software_manager.remove(args):
            log.info(MESSAGES[action]["success"], args)
            return exit_codes.UTILITY_OK
        log.error(MESSAGES[action]["fail"], args)
        return exit_codes.UTILITY_FAIL

    def check_installed():
        if software_manager.check_installed(args):
            log.info(MESSAGES[action]["success"], args)
            return exit_codes.UTILITY_OK
        log.info(MESSAGES[action]["fail"], args)
        return exit_codes.UTILITY_FAIL

    def list_all():
        for pkg in software_manager.list_all():
            log.info(pkg)
        return exit_codes.UTILITY_OK

    def list_files():
        for f in software_manager.list_files(args):
            log.info(f)
        return exit_codes.UTILITY_OK

    def add_repo():
        if software_manager.add_repo(args):
            log.info(MESSAGES[action]["success"], args)
            return exit_codes.UTILITY_OK
        log.error(MESSAGES[action]["fail"], args)
        return exit_codes.UTILITY_FAIL

    def remove_repo():
        if software_manager.remove_repo(args):
            log.info(MESSAGES[action]["success"], args)
            return exit_codes.UTILITY_OK
        log.error(MESSAGES[action]["fail"], args)
        return exit_codes.UTILITY_FAIL

    def upgrade():
        if software_manager.upgrade():
            log.info(MESSAGES[action])
        return exit_codes.UTILITY_OK

    def what_provides():
        provides = software_manager.provides(args)
        if provides is not None:
            log.info(MESSAGES[action], provides, args)
        return exit_codes.UTILITY_OK

    def install_what_provides():
        if software_manager.install_what_provides(args):
            log.info(MESSAGES[action], args)
        return exit_codes.UTILITY_OK

    def show_help():
        parser.print_help()
        return exit_codes.UTILITY_OK

    parser = argparse.ArgumentParser(
        "install|remove|check-installed|list-all|list-files|add-repo|"
        "remove-repo|upgrade|what-provides|install-what-provides arguments"
    )
    parser.add_argument(
        "--verbose",
        dest="debug",
        action="store_true",
        help="include debug messages in console output",
    )

    namespace, args = parser.parse_known_args()

    if namespace.debug:
        logging.basicConfig(level=logging.DEBUG, format="%(message)s")
    else:
        logging.basicConfig(level=logging.INFO, format="%(message)s")

    software_manager = SoftwareManager()
    if not software_manager.is_capable():
        log.error(
            "ERROR: There is no backend implementation for this system. No "
            "action will be performed."
        )
        return exit_codes.UTILITY_FAIL

    options = {
        "install": install,
        "remove": remove,
        "check-installed": check_installed,
        "list-all": list_all,
        "list-files": list_files,
        "add-repo": add_repo,
        "remove-repo": remove_repo,
        "upgrade": upgrade,
        "what-provides": what_provides,
        "install-what-provides": install_what_provides,
        "show-help": show_help,
    }

    if args:
        action = args[0]
        args = " ".join(args[1:])
    else:
        action = "show-help"

    return options[action]()
