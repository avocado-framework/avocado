#!/usr/bin/env python3
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: Red Hat Inc. 2020
# Authors: Beraldo Leal <bleal@redhat.com>

"""
This example shows a basic command line to download output test files.

Please note that this is a working in progress and has the Nrun architecture in
mind. This should be evolved to a avocado command line like this:

    $ avocado job <job_id> download-outputs <task-id>

In order to run this example you need first to run a test that will save output
files inside `test-results/<task_id>/data` folder. You can create files there
manually if necessary.
"""

import sys
import json
import os

from avocado.core.spawners.process import ProcessSpawner
from avocado.core.spawners.podman import PodmanSpawner
from avocado.core.spawners.exceptions import SpawnerException


def discover_spawner(job_id):
    """Fake discover spawner. This is a mock.

    Soon, we need to generate the results.json file with a spawner key.
    """
    try:
        filename = "~/avocado/job-results/{}/results.json".format(job_id)
        job_data = json.loads(filename)
        return job_data.get('spawner')
    except Exception:   # pylint: disable=broad-except
        return 'ProcessSpawner'


def process_args():
    """Basic args processing."""
    if len(sys.argv) != 4:
        print("Usage: ./download.py JOB_ID TASK_ID DESTINATION_PATH")
        sys.exit(-1)
    return sys.argv[1], sys.argv[2], sys.argv[3]


def save_stream_to_file(stream, filename):
    """Save stream to a file.

    Directory must exists before calling this function.
    """
    dirname = os.path.dirname(filename)
    if not os.path.isdir(dirname):
        print("Error: {} do not exists. Exiting...".format(dirname))
        sys.exit(-1)

    with open(filename, 'ab') as output:
        output.write(stream)


def main():
    """Basic example on how a download client command line could be.

    This probably will be integrated with the following command line:

      $ avocado job <id> download-output <task-id>

    Or something like that.
    """
    job_id, task_id, dst_path = process_args()
    spawner_name = discover_spawner(job_id)
    if spawner_name == 'ProcessSpawner':
        spawner = ProcessSpawner()
    elif spawner_name == 'PodmanSpawner':
        spawner = PodmanSpawner()

    print("Downloading...")
    try:
        for filename, stream in spawner.stream_output(job_id, task_id):
            destination = os.path.join(dst_path, filename)
            save_stream_to_file(stream, destination)
    except SpawnerException as ex:
        print("Error: Failed to download: {}. Exiting...".format(ex))
        sys.exit(-1)


if __name__ == '__main__':
    main()
