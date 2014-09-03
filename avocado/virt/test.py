from avocado import test


class VirtTest(test.Test):

    def __init__(self, methodName='runTest', name=None, params=None,
                 base_logdir=None, tag=None, job=None, runner_queue=None):

        if job.args.qemu_bin:
            params['qemu_bin'] = job.args.qemu_bin
        if job.args.qemu_dst_bin:
            params['qemu_dst_bin'] = job.args.qemu_dst_bin

        super(VirtTest, self).__init__(methodName=methodName, name=name,
                                       params=params, base_logdir=base_logdir,
                                       tag=tag, job=job,
                                       runner_queue=runner_queue)
