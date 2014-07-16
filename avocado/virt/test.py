import os
import imp

from avocado import test
from avocado.virt import env


class VirtTest(test.Test):
    default_params = {}

    def setup(self):
        self.env_filename = os.path.join(self.workdir, 'env')
        self.env = env.Env(self.env_filename, params=self.params, test=self)
        self.subtestdir = os.path.join(self.basedir, 'subtests')
        self.subtest = self.load_subtest()

    def load_subtest(self):
        f, p, d = imp.find_module(self.params.get('t_type'), [self.subtestdir])
        test_module = imp.load_module(self.params.get('t_type'), f, p, d)
        f.close()
        return getattr(test_module, 'run')

    def action(self):
        self.env.pre_process()
        self.subtest(self, self.params)
        self.env.post_process()
        self.env.save()
