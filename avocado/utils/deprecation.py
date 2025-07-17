import logging

LOGGER = logging.getLogger(__name__)


class LogDeprecation:
    """
    A class that ensures a message is logged only once.
    """

    def __init__(self):
        self._logged = set()

    def warning(self, utility_name, msg=None):
        """
        Logs a warning message only once.
        """
        if msg is None:
            msg = (
                f"The {utility_name} utility is deprecated. "
                "It has been moved to the AAutils project "
                "and will be removed after the next LTS release. "
                "For more information, please see the following "
                "link: https://github.com/avocado-framework/aautils"
            )
        if utility_name not in self._logged:
            LOGGER.warning(msg)
            self._logged.add(utility_name)


log_deprecation = LogDeprecation()
