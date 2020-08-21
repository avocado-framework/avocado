import time

from avocado.utils.process import SubProcess
from avocado.utils.ssh import Session

with Session('host', user='root', key='/path/to/key') as s:
    print('connected')
    procs = []
    cmd = s.get_raw_ssh_command('sleep 5')
    for i in range(10):
        p = SubProcess(cmd)
        print(p.start())
        procs.append(p)

    while True:
        for proc in procs:
            proc.poll()

        if all([p.result.exit_status is not None for p in procs]):
            print('all finished')
            break

        time.sleep(1)
        print('working...')

print('session closed')
