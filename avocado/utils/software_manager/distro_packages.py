import logging
import os

from avocado.utils import distro
from avocado.utils.software_manager.manager import SoftwareManager

log = logging.getLogger('avocado.utils.software_manager')


def install_distro_packages(distro_pkg_map, interactive=False):
    """
    Installs packages for the currently running distribution

    This utility function checks if the currently running distro is a
    key in the distro_pkg_map dictionary, and if there is a list of packages
    set as its value.

    If these conditions match, the packages will be installed using the
    software manager interface, thus the native packaging system if the
    currently running distro.

    :type distro_pkg_map: dict
    :param distro_pkg_map: mapping of distro name, as returned by
        utils.get_os_vendor(), to a list of package names
    :return: True if any packages were actually installed, False otherwise
    """
    if not interactive:
        os.environ['DEBIAN_FRONTEND'] = 'noninteractive'

    result = False
    pkgs = []
    detected_distro = distro.detect()

    distro_specs = [spec for spec in distro_pkg_map if
                    isinstance(spec, distro.Spec)]

    for distro_spec in distro_specs:
        if distro_spec.name != detected_distro.name:
            continue

        if (distro_spec.arch is not None and
                distro_spec.arch != detected_distro.arch):
            continue

        if int(detected_distro.version) < distro_spec.min_version:
            continue

        if (distro_spec.min_release is not None and
                int(detected_distro.release) < distro_spec.min_release):
            continue

        pkgs = distro_pkg_map[distro_spec]
        break

    if not pkgs:
        log.info("No specific distro release package list")

        # when comparing distro names only, fallback to a lowercase version
        # of the distro name is it's more common than the case as detected
        pkgs = distro_pkg_map.get(detected_distro.name, None)
        if not pkgs:
            pkgs = distro_pkg_map.get(detected_distro.name.lower(), None)

        if not pkgs:
            log.error("No generic distro package list")

    if pkgs:
        needed_pkgs = []
        software_manager = SoftwareManager()
        for pkg in pkgs:
            if not software_manager.check_installed(pkg):
                needed_pkgs.append(pkg)
        if needed_pkgs:
            text = ' '.join(needed_pkgs)
            log.info('Installing packages "%s"', text)
            result = software_manager.install(text)
    else:
        log.error("No packages found for %s %s %s %s",
                  detected_distro.name, detected_distro.arch,
                  detected_distro.version, detected_distro.release)
    return result
