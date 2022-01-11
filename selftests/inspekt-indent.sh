#!/bin/sh -e
echo "** Running inspekt-indent..."

inspekt indent --exclude=.git
