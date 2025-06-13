import logging

import avocado


class Test(avocado.Test):
    def test(self):
        CUSTOM_LEVEL = 35
        logger = logging.getLogger("custom_logger")
        logger.setLevel(CUSTOM_LEVEL)
        logger.log(
            CUSTOM_LEVEL,
            "Custom logger and level message",
        )
