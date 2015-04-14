"""
Please don't get inspired by this ugly code
"""
import sys


sys.stdout.write("Direct output to stdout\n")
sys.stderr.write("Direct output to stderr\n")
raw_input("I really want some input on each import")
sys.stdin = 'This is my __COOL__ stdin'
sys.stdout = 'my stdout'
sys.stderr = 'my stderr'
sys.exit(-1)    # Exit even on import
