from avocado.utils.software_manager.inspector import (
    SUPPORTED_PACKAGE_MANAGERS, SystemInspector)


class SoftwareManager:

    """
    Package management abstraction layer.

    It supports a set of common package operations for testing purposes, and it
    uses the concept of a backend, a helper class that implements the set of
    operations of a given package management tool.
    """

    def __init__(self):
        """
        Lazily instantiate the object
        """
        self.initialized = False
        self.backend = None
        self.lowlevel_base_command = None
        self.base_command = None
        self.pm_version = None

    def _init_on_demand(self):
        """
        Determines the best supported package management system for the given
        operating system running and initializes the appropriate backend.
        """
        if not self.initialized:
            inspector = SystemInspector()
            backend_type = inspector.get_package_management()

            if backend_type not in SUPPORTED_PACKAGE_MANAGERS:
                raise NotImplementedError(f'Unimplemented package management '
                                          f'system: {backend_type}.')

            backend = SUPPORTED_PACKAGE_MANAGERS[backend_type]
            self.backend = backend()
            self.initialized = True

    def __getattr__(self, name):
        self._init_on_demand()
        return self.backend.__getattribute__(name)

    def is_capable(self):
        """Checks if environment is capable by initializing the backend."""
        try:
            self._init_on_demand()
        except NotImplementedError:
            pass
        return self.initialized

    @staticmethod
    def extract_from_package(package_path, dest_path=None):
        """Try to extract a package content into a destination directory.

        It will try to see if the package is valid against all supported
        package managers and if any is found, then extracts its content into
        the extract_path.

        Raises NotImplementedError when a non-supported package is used.

        :param str package_path: package file path.
        :param str dest_path: destination path to extract. Default is the
                              current directory.
        :returns: destination path were the package it was extracted.
        """
        for backend in SUPPORTED_PACKAGE_MANAGERS.values():
            if backend.is_valid(package_path):
                return backend.extract_from_package(package_path, dest_path)
        raise NotImplementedError(f'No package manager supported was found '
                                  f'for package {package_path}.')
