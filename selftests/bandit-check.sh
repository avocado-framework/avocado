#!/bin/sh -e

echo "** Running bandit..."

#  Only reporting on the high-severity issues with -lll
bandit -r -lll .
