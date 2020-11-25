import asyncio
import struct


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
        self._uri = uri
        self._repo = repo
        self._server_task = None

    async def create_server(self):
        if ':' in self._uri:
            host, port = self._uri.split(':')
            port = int(port)
            self._server_task = await asyncio.start_server(
                self.cb,
                host=host,
                port=port)
        else:
            self._server_task = await asyncio.start_unix_server(
                self.cb,
                path=self._uri)

    async def serve_forever(self):
        if self._server_task is None:
            await self.create_server()
        await self._server_task.serve_forever()

    def close(self):
        self._server_task.close()

    async def cb(self, reader, _):
        while True:
            # First 8 bytes are the message size
            size = await reader.readexactly(8)
            if not size:
                break

            size = struct.unpack('!Q', size)[0]
            left, chunk = size, b''
            while left > 0:
                chunk_size = min(4096, left)
                chunk += await reader.readexactly(chunk_size)
                left -= chunk_size

            raw_message = struct.unpack('!{}s'.format(size),
                                        chunk)[0].decode('ascii')
            self._repo.process_raw_message(raw_message)
