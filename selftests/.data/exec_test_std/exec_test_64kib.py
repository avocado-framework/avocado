#!/usr/bin/env python3

import sys

if __name__ == "__main__":
    data = b"1" * 1024 * 64
    sys.stdout.write(data.decode())
    data = b"2" * 1024 * 64
    sys.stderr.write(data.decode())
