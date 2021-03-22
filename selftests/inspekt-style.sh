#!/bin/sh -e
echo "** Running inspekt-style..."

inspekt style . --exclude=.git --disable E501,E402,E722
