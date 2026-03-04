import asyncio
import os
import socket

from avocado.core.settings import settings
from avocado.core.output import LOG_JOB


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

    last_exc = None
    for port in range(start, end + 1):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, port))
            return f"{host}:{port}"
        except OSError as exc:
            last_exc = exc
        finally:
            sock.close()

    raise OSError(
        f"Could not bind status server to any port in range {start}-{end} on {host}: {last_exc}"
    )


class StatusServer:
    """Server that listens for status messages and updates a StatusRepo."""

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
            LOG_JOB.info("Status server listening on %s", self._uri)
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
        self._server_task.close()
        if os.path.exists(self._uri):
            os.unlink(self._uri)

    async def cb(self, reader, _):
        while True:
            try:
                raw_message = await reader.readline()
            except ConnectionResetError:
                continue
            if not raw_message:
                return
            self._repo.process_raw_message(raw_message)
