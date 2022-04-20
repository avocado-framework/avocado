import time
from multiprocessing import Process, SimpleQueue

from avocado.core.nrunner.app import BaseRunnerApp
from avocado.core.nrunner.runner import RUNNER_RUN_STATUS_INTERVAL, BaseRunner
from avocado.core.settings import settings
from avocado.utils import data_structures
from avocado.utils.asset import Asset


class AssetRunner(BaseRunner):
    """Runner for dependencies of type package

    This runner handles the fetch of files using the Avocado Assets utility.

    Runnable attributes usage:

     * kind: 'asset'

     * uri: not used

     * args: not used

     * kwargs:
        - name: the file name or uri (required)
        - asset_hash: hash of the file (optional)
        - algorithm: hash algorithm (optional)
        - locations: location(s) where the file can be fetched from (optional)
        - expire: time in seconds for the asset to expire (optional)
    """

    name = 'asset'
    description = 'Runner for dependencies of type package'

    CONFIGURATION_USED = ['datadir.paths.cache_dirs']

    @staticmethod
    def _fetch_asset(name, asset_hash, algorithm, locations, cache_dirs,
                     expire, queue):

        asset_manager = Asset(name, asset_hash, algorithm, locations,
                              cache_dirs, expire)

        result = 'pass'
        stdout = ''
        stderr = ''
        try:
            asset_file = asset_manager.fetch()
            stdout = f'File fetched at {asset_file}'
        except OSError as exc:
            result = 'error'
            stderr = str(exc)

        output = {'result': result,
                  'stdout': stdout,
                  'stderr': stderr}
        queue.put(output)

    def run(self, runnable):
        # pylint: disable=W0201
        self.runnable = runnable
        yield self.prepare_status('started')

        name = self.runnable.kwargs.get('name')
        # if name was passed correctly, run the Avocado Asset utility
        if name is not None:
            asset_hash = self.runnable.kwargs.get('asset_hash')
            algorithm = self.runnable.kwargs.get('algorithm')
            locations = self.runnable.kwargs.get('locations')
            expire = self.runnable.kwargs.get('expire')
            if expire is not None:
                expire = data_structures.time_to_seconds(str(expire))

            cache_dirs = self.runnable.config.get('datadir.paths.cache_dirs')
            if cache_dirs is None:
                cache_dirs = settings.as_dict().get('datadir.paths.cache_dirs')

            # let's spawn it to another process to be able to update the
            # status messages and avoid the Asset to lock this process
            queue = SimpleQueue()
            process = Process(target=self._fetch_asset,
                              args=(name, asset_hash, algorithm, locations,
                                    cache_dirs, expire, queue))
            process.start()

            while queue.empty():
                time.sleep(RUNNER_RUN_STATUS_INTERVAL)
                yield self.prepare_status('running')

            output = queue.get()
            result = output['result']
            stdout = output['stdout']
            stderr = output['stderr']
        else:
            # Otherwise, log the missing package name
            result = 'error'
            stdout = ''
            stderr = ('At least name should be passed as kwargs using'
                      ' name="uri".')

        yield self.prepare_status('running',
                                  {'type': 'stdout',
                                   'log': stdout.encode()})
        yield self.prepare_status('running',
                                  {'type': 'stderr',
                                   'log': stderr.encode()})
        yield self.prepare_status('finished', {'result': result})


class RunnerApp(BaseRunnerApp):
    PROG_NAME = 'avocado-runner-asset'
    PROG_DESCRIPTION = ('nrunner application for dependencies of type asset')
    RUNNABLE_KINDS_CAPABLE = ['asset']


def main():
    app = RunnerApp(print)
    app.run()


if __name__ == '__main__':
    main()
