# This module was introduced only for AAutils migration purposes and will be removed
# after the AAutils migration is complete. No need to migrate this module to AAutils.

import logging

LOGGER = logging.getLogger(__name__)


class LogDeprecation:
    """
    A class that ensures a message is logged only once.
    """

    def __init__(self):
        self._logged = set()
        self._logged_messages = set()

    def warning(self, utility_name, msg=None):
        """
        Logs a warning message only once.
        """
        if msg is None:
            self._logged.add(utility_name)
        else:
            self._logged_messages.add(msg)

    def flush(self):
        for msg in self._logged_messages:
            LOGGER.info(msg)
        for utility_name in self._logged:
            msg = (
                f"The {utility_name} utility is deprecated. "
                "It has been moved to the AAutils project "
                "and will be removed after the next LTS release. "
                "For more information, please see the following "
                "link: https://github.com/avocado-framework/aautils"
            )
            LOGGER.info(msg)
        self._logged_messages.clear()
        self._logged.clear()


log_deprecation = LogDeprecation()
