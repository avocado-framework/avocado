#!/usr/bin/env python

import os
import multiprocessing

from avocado import Test
from avocado import main
from avocado.utils import archive
from avocado.utils import disk
from avocado.utils import build
from avocado.utils import memory
from avocado.utils import process


class Stress(Test):

    """
    Calls stress, a simple program which aims to impose certain types of
    computing stress on the target machine.
    @author: Yi Yang (yang.y.yi@gmail.com)
    """

    def setUp(self):
        """
        Build 'stress'.
        Source:
         http://people.seas.harvard.edu/~apw/stress/stress-1.0.4.tar.gz
        """
        stress_tarball = self.params.get('stress_tarball',
                                         default='stress-1.0.4.tar.gz')
        tarball_path = self.get_data_path(stress_tarball)
        archive.extract(tarball_path, self.srcdir)
        stress_version = stress_tarball.split('.tar.')[0]
        self.srcdir = os.path.join(self.srcdir, stress_version)
        os.chdir(self.srcdir)
        process.run('./configure')
        build.make(self.srcdir)

    def test(self):
        """
        Execute 'stress' with proper arguments.
        """
        length = self.params.get('stress_lenght', default=60)
        threads = self.params.get('threads', default=None)
        memory_per_thread = self.params.get('memory_per_thread', default=None)
        file_size_per_thread = self.params.get('file_size_per_thread',
                                               default=None)
        if threads is None:
            # We will use 2 workers of each type for each CPU detected
            threads = 2 * multiprocessing.cpu_count()

        if memory_per_thread is None:
            # Sometimes the default memory used by each memory worker (256 M)
            # might make our machine go OOM and then funny things might start to
            # happen. Let's avoid that.
            mb = (memory.freememtotal() +
                  memory.read_from_meminfo('SwapFree') / 2)
            memory_per_thread = (mb * 1024) / threads

        if file_size_per_thread is None:
            # Even though unlikely, it's good to prevent from allocating more
            # disk than this machine actually has on its autotest directory
            # (limit the amount of disk used to max of 90 % of free space)
            free_disk = disk.freespace(self.srcdir)
            file_size_per_thread = 1024 ** 2
            if (0.9 * free_disk) < file_size_per_thread * threads:
                file_size_per_thread = (0.9 * free_disk) / threads

        # Number of CPU workers spinning on sqrt()
        args = '--cpu %d ' % threads
        # Number of IO workers spinning on sync()
        args += '--io %d ' % threads
        # Number of Memory workers spinning on malloc()/free()
        args += '--vm %d ' % threads
        # Amount of memory used per each worker
        args += '--vm-bytes %d ' % memory_per_thread
        # Number of HD workers spinning on write()/ulink()
        args += '--hdd %d ' % threads
        # Size of the files created by each worker in bytes
        args += '--hdd-bytes %d ' % file_size_per_thread
        # Time for which the stress test will run
        args += '--timeout %d ' % length
        # Verbose flag
        args += '--verbose'

        os.chdir(self.srcdir)
        cmd = ('./src/stress %s' % args)
        process.run(cmd)

if __name__ == "__main__":
    main()
