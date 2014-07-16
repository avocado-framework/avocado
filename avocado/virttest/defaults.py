from autotest.client.shared import distro

DEFAULT_MACHINE_TYPE = "i440fx"
DEFAULT_GUEST_OS = "JeOS.19"


def get_default_guest_os_info():
    """
    Gets the default asset and variant information depending on host OS
    """
    os_info = {'asset': 'jeos-19-64', 'variant': DEFAULT_GUEST_OS}

    detected = distro.detect()
    if detected.name == 'fedora' and int(detected.version) >= 20:
        os_info = {'asset': 'jeos-20-64', 'variant': 'JeOS.20'}

    return os_info
