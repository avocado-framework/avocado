#!/bin/sh

# Put here the name of your GIT remote that tracks the official
# repo, that is, https://github.com/avocado-framework/avocado
# (or the git:// url version of the same repo)
ORIGIN=origin

git fetch $ORIGIN

ORIGIN_MASTER_COMMIT=$(git log --pretty=format:'%h' -n 1 $ORIGIN/master)

PODMAN=$(which podman)
PODMAN_IMAGE=fedora:33

$PODMAN run --rm -ti $PODMAN_IMAGE /bin/bash -c "dnf -y module disable avocado && dnf -y install 'dnf-command(copr)' && dnf -y copr enable @avocado/avocado-latest && dnf -y install python3-avocado && (rpm -q python3-avocado | grep $ORIGIN_MASTER_COMMIT)"
