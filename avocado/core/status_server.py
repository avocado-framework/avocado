import asyncio
import base64
import json


def json_loads(data):
    if isinstance(data, bytes):
        data = data.decode()
    return json.loads(data, object_hook=json_base64_decode)


def json_base64_decode(dct):
    if '__base64_encoded__' in dct:
        return base64.b64decode(dct['__base64_encoded__'])
    return dct


class StatusServer:

    def __init__(self, uri, tasks_pending=None, verbose=False):
        self.uri = uri
        self.server_task = None
        self.result = {}
        if tasks_pending is None:
            tasks_pending = []
        self.tasks_pending = tasks_pending
        self.verbose = verbose
        self.wait_on_tasks_pending = len(self.tasks_pending) > 0

    async def cb(self, reader, _):
        while True:
            if self.wait_on_tasks_pending:
                if not self.tasks_pending:
                    print('Status server: exiting due to all tasks finished')
                    self.server_task.cancel()
                    await self.server_task
                    return True

            message = await reader.readline()
            message = message.strip()
            if message == b'bye':
                print('Status server: exiting due to user request')
                self.server_task.cancel()
                await self.server_task
                return True

            if not message:
                return False

            try:
                data = json_loads(message)
            except json.decoder.JSONDecodeError:
                return False

            if data.get('status') in ['started']:
                self.handle_task_started(data)
            elif data.get('status') in ['finished']:
                self.handle_task_finished(data)

    async def create_server_task(self):
        host, port = self.uri.split(':')
        port = int(port)
        server = await asyncio.start_server(self.cb, host=host, port=port)
        print("Status server started at:", self.uri)
        await server.wait_closed()

    def handle_task_started(self, data):
        if self.verbose:
            print("Task started: {}. Outputdir: {}".format(data['id'],
                                                           data['output_dir']))

    def handle_task_finished(self, data):
        if 'result' not in data:
            return

        result = data['result']
        task_id = data['id']

        if self.wait_on_tasks_pending:
            self.tasks_pending.remove(task_id)

        if result not in self.result:
            self.result[result] = []
        self.result[result].append(task_id)

        if self.verbose:
            print('Task complete (%s): %s' % (result, task_id))
            if result not in ('pass', 'skip'):
                stdout = data.get('stdout', b'')
                if stdout:
                    print('Task %s stdout:\n%s\n' % (task_id, stdout))
                stderr = data.get('stderr', b'')
                if stderr:
                    print('Task %s stderr:\n%s\n' % (task_id, stderr))
                output = data.get('output', b'')
                if output:
                    print('Task %s output:\n%s\n' % (task_id, output))

    def start(self):
        loop = asyncio.get_event_loop()
        self.server_task = loop.create_task(self.create_server_task())

    async def wait(self):
        while not self.server_task.done():
            await asyncio.sleep(0.1)
