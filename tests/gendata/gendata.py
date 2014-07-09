#!/usr/bin/python

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
# Copyright: Red Hat Inc. 2014
# Author: Cleber Rosa <cleber@redhat.com>

import os

from avocado import test
from avocado import job


class gendata(test.Test):

    """
    Simple test that generates data to be persisted after the test is run
    """

    def generate_bsod(self):
        try:
            from PIL import Image
            from PIL import ImageDraw
        except ImportError:
            return

        text = ["DREADED BLUE SCREEN OF DEATH"]
        dmesg_path = os.path.join(self.job.debugdir, "sysinfo", "pre", "dmesg_-c")
        self.log.info("dmesg_path: %s", dmesg_path)
        if os.path.exists(dmesg_path):
            dmesg = open(dmesg_path)
            text = dmesg.readlines()[0:50]

        bsod = Image.new("RGB", (640, 480), "blue")
        draw = ImageDraw.Draw(bsod)
        x = y = 2
        for line in text:
            draw.text((2, y), line)
            y += 12
        bsod.save(os.path.join(self.datadir, "bsod.png"))

    def generate_json(self):
        import json
        output_path = os.path.join(self.datadir, "test.json")
        output = {"basedir": self.basedir,
                  "datadir": self.datadir}
        json.dump(output, open(output_path, "w"))

    def action(self):
        self.generate_bsod()
        self.generate_json()

if __name__ == "__main__":
    job.main()
