#!/usr/bin/python

import os

import avocado


class GenDataTest(avocado.Test):

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
        dmesg_path = os.path.join(self.job.logdir, "sysinfo", "pre", "dmesg_-c")
        self.log.info("dmesg_path: %s", dmesg_path)
        if os.path.exists(dmesg_path):
            dmesg = open(dmesg_path)
            text = dmesg.readlines()[0:50]

        bsod = Image.new("RGB", (640, 480), "blue")
        draw = ImageDraw.Draw(bsod)
        y = 2
        for line in text:
            draw.text((2, y), line)
            y += 12
        bsod.save(os.path.join(self.outputdir, "bsod.png"))

    def generate_json(self):
        import json
        output_path = os.path.join(self.outputdir, "test.json")
        output = {"basedir": self.basedir,
                  "outputdir": self.outputdir}
        json.dump(output, open(output_path, "w"))

    def action(self):
        self.generate_bsod()
        self.generate_json()

if __name__ == "__main__":
    avocado.main()
