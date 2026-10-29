import asyncio
import logging
import os

from avocado.core.settings import settings
from avocado.core.status.utils import StatusMsgInvalidJSONError

LOG = logging.getLogger(__name__)


class StatusServer:
    """Server that listens for status messages and updates a StatusRepo."""

    # Buffered records can be read without suspending the event loop.
    _RECORDS_PER_EVENT_LOOP_TURN = 64

    def __init__(self, uri, repo):
        """Initializes a new StatusServer.

        :param uri: either a "host:port" string or a path to a UNIX socket
        :type uri: str
        :param repo: the repository to use to process received status
                     messages
        :type repo: :class:`avocado.core.status.repo.StatusRepo`
        """
        self._uri = uri
        self._repo = repo
        self._server_task = None

    @property
    def uri(self):
        return self._uri

    async def create_server(self):
        limit = settings.as_dict().get("run.status_server_buffer_size")
        if ":" in self._uri:
            host, port = self._uri.split(":")
            port = int(port)
            self._server_task = await asyncio.start_server(
                self.cb, host=host, port=port, limit=limit
            )
        else:
            self._server_task = await asyncio.start_unix_server(
                self.cb, path=self._uri, limit=limit
            )

    async def serve_forever(self):
        if self._server_task is None:
            await self.create_server()

        await self._server_task.serve_forever()

    def close(self):
        self._server_task.close()
        if os.path.exists(self._uri):
            os.unlink(self._uri)

    async def cb(self, reader, _):
        records_this_turn = 0
        while True:
            try:
                raw_message = await reader.readline()
            except ConnectionResetError as e:
                LOG.warning("Connection was reset: %s", e)
                return
            except BrokenPipeError as e:
                LOG.warning("Broken pipe: %s", e)
                return
            if not raw_message:
                return
            try:
                self._repo.process_raw_message(raw_message)
            except StatusMsgInvalidJSONError as e:
                LOG.warning("Invalid JSON in internal status message: %s", e)

            records_this_turn += 1
            if records_this_turn >= self._RECORDS_PER_EVENT_LOOP_TURN:
                records_this_turn = 0
                await asyncio.sleep(0)
