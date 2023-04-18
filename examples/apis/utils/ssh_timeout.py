import time

from avocado.utils.ssh import Session

with Session("host", user="root", key="/path/to/key") as s:
    # baseline case
    time_start = time.monotonic()
    s.cmd("sleep 10")
    total_time = time.monotonic() - time_start
    print(total_time)
    assert total_time >= 10

    # check of timeout enforcement
    time_start = time.monotonic()
    s.cmd("sleep 10", timeout=1)
    total_time = time.monotonic() - time_start
    print(total_time)
    assert total_time <= 10
