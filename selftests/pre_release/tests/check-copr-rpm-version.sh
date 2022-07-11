#!/bin/sh -e

# Put here the name of your GIT remote that tracks the official
# repo, that is, https://github.com/avocado-framework/avocado
# (or the git:// url version of the same repo)
ORIGIN=origin

git fetch $ORIGIN

ORIGIN_MASTER_COMMIT=$(git log --pretty=format:'%h' -n 1 $ORIGIN/master)
VERSION=$(python setup.py --version 2>/dev/null)
COMMIT_DATE=$(git log --pretty='format:%cd' --date='format:%Y%m%d' -n 1 $ORIGIN/master)
SHORT_COMMIT=$(git rev-parse --short=9 $ORIGIN/master)
RPM_RELEASE_NUMBER=$(grep -E '^Release:\s([0-9]+)' python-avocado.spec | sed -E 's/Release:\s([0-9]+).*/\1/')
DISTRO_VERSION=36

RPM_NVR="python3-avocado-${VERSION}-${RPM_RELEASE_NUMBER}.${COMMIT_DATE}git${SHORT_COMMIT}.fc${DISTRO_VERSION}"

PODMAN=$(which podman 2>/dev/null || which docker)
PODMAN_IMAGE=quay.io/avocado-framework/check-copr-rpm-version

$PODMAN run --rm -ti $PODMAN_IMAGE /bin/bash -c "dnf -y install ${RPM_NVR}"
