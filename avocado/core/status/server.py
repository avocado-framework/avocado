import asyncio
import logging
import os

from avocado.core.output import LOG_JOB
from avocado.core.settings import settings
from avocado.core.status.repo import StatusMsgMissingDataError
from avocado.core.status.utils import StatusMsgInvalidJSONError
from avocado.utils.network import ports as network_ports

LOG = logging.getLogger(__name__)


def resolve_listen_uri(uri):
    """
    Normalize a status server URI that may contain a port range into
    a concrete "host:port" endpoint.
    """
    if ":" not in uri:
        return uri
    host, port_spec = uri.rsplit(":", 1)
    if "-" not in port_spec:
        return uri

    start_s, end_s = port_spec.split("-", 1)
    start = int(start_s)
    end = int(end_s)
    if start > end:
        raise ValueError(
            f"Invalid port range (start > end) in status server URI: {uri}"
        )

    port = network_ports.find_free_port(
        start_port=start,
        end_port=end,
        address=host,
        sequent=True,
    )
    if port is None:
        raise OSError(
            f"Could not bind status server to any port in range {start}-{end} on {host}"
        )
    return f"{host}:{port}"


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
        self._uri = resolve_listen_uri(uri)
        self._repo = repo
        self._server_task = None
        self._connections = set()

    @property
    def uri(self):
        return self._uri

    async def create_server(self):
        limit = settings.as_dict().get("run.status_server_buffer_size")
        if ":" in self._uri:
            host, port = self._uri.rsplit(":", 1)
            port = int(port)
            self._server_task = await asyncio.start_server(
                self.cb, host=host, port=port, limit=limit
            )
        else:
            self._server_task = await asyncio.start_unix_server(
                self.cb, path=self._uri, limit=limit
            )
        LOG_JOB.info("Status server listening on %s", self._uri)

    async def serve_forever(self):
        if self._server_task is None:
            await self.create_server()

        await self._server_task.serve_forever()

    def close(self):
        if self._server_task is None:
            return
        self._server_task.close()
        for writer in tuple(self._connections):
            try:
                writer.close()
            except OSError as error:
                LOG.debug("Error closing status client connection: %s", error)
        if ":" not in self._uri:
            try:
                os.unlink(self._uri)
            except FileNotFoundError:
                pass

    async def wait_closed(self):
        """Wait for the listener and tracked client connections to close."""
        if self._server_task is not None:
            await self._server_task.wait_closed()
        for writer in tuple(self._connections):
            try:
                await writer.wait_closed()
            except OSError as error:
                LOG.debug("Error closing status client connection: %s", error)

    async def cb(self, reader, writer):
        if writer is not None:
            self._connections.add(writer)
        try:
            if self._server_task is not None and not self._server_task.is_serving():
                return
            records_this_turn = 0
            while True:
                try:
                    raw_message = await reader.readline()
                except ValueError as e:
                    LOG.error("Status message exceeded the stream buffer limit: %s", e)
                except ConnectionResetError as e:
                    LOG.warning("Connection was reset: %s", e)
                    return
                except BrokenPipeError as e:
                    LOG.warning("Broken pipe: %s", e)
                    return
                except OSError as e:
                    LOG.warning("I/O error reading status message: %s", e)
                    return
                else:
                    if not raw_message:
                        return
                    try:
                        self._repo.process_raw_message(raw_message)
                    except StatusMsgInvalidJSONError as e:
                        LOG.warning("Invalid JSON in internal status message: %s", e)
                    except StatusMsgMissingDataError:
                        LOG.exception("Missing data in internal status message")

                records_this_turn += 1
                if records_this_turn >= self._RECORDS_PER_EVENT_LOOP_TURN:
                    records_this_turn = 0
                    await asyncio.sleep(0)
        finally:
            if writer is not None:
                try:
                    writer.close()
                    await writer.wait_closed()
                except OSError as error:
                    LOG.debug("Error closing status client connection: %s", error)
                finally:
                    self._connections.discard(writer)
