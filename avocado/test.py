import os
import time
from avocado.core import data_dir


class Test(object):

    """
    Represents an avocado test.
    """

    def __init__(self, name, tag):
        self.name = name
        self.tag = tag
        self.basedir = os.path.join(data_dir.get_root_dir(),
                                    '%s.%s' % (name, tag))
        self.srcdir = os.path.join(self.basedir, 'src')
        self.tmpdir = os.path.join(self.basedir, 'tmp')

        self.debugdir = None
        self.outputdir = None
        self.resultsdir = None
        self.logfile = None
        self.status = None

        self.time_elapsed = None

    def setup(self):
        pass

    def action(self):
        pass

    def run(self):
        start_time = time.time()
        try:
            self.action()
            self.status = 'PASS'
        except:
            self.status = 'FAIL'

        end_time = time.time()
        self.time_elapsed = end_time - start_time
        return self.status == 'PASS'

    def cleanup(self):
        pass
