import asyncio

from avocado import Test


class AsyncSleepTest(Test):

    """
    This test sleeps for 1s by default

    :param sleep_length: Sleep duration
    """

    async def test(self):
        """
        Sleep for length seconds.
        """
        sleep_length = float(self.params.get('sleep_length', default=1))
        self.log.debug("Sleeping for %.2f seconds", sleep_length)
        await asyncio.sleep(sleep_length)
