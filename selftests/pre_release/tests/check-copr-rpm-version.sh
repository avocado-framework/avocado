#!/bin/sh -e

# This script accepts a package NVR as its first argument.  If not given,
# it will default to a version-only check against the COPR repo to verify
# that a recent snapshot build for the current VERSION is available.

# Put here the name of your GIT remote that tracks the official
# repo, that is, https://github.com/avocado-framework/avocado
# (or the git:// url version of the same repo)
ORIGIN=origin

git fetch $ORIGIN

VERSION=$(python setup.py --version 2>/dev/null)
DISTRO_VERSION=42

PODMAN=$(which podman 2>/dev/null || which docker)
PODMAN_IMAGE=quay.io/avocado-framework/check-copr-rpm-version

if [ -z "$PODMAN" ]; then
    echo "ERROR: Neither podman nor docker was found in PATH."
    exit 1
fi

# If an explicit NVR was provided as $1, use exact-match install (legacy behaviour).
# Otherwise verify that COPR carries *any* snapshot build for the current VERSION.
if [ -n "$1" ]; then
    RPM_NVR="$1"
    echo "Checking for explicit NVR: ${RPM_NVR}"
    DNF_CMD="dnf -y install ${RPM_NVR}"
else
    # COPR builds snapshot RPMs whose release encodes the commit hash of the
    # master tip *at build time*.  That commit may differ from the current
    # master tip when the script runs (e.g. after a merge commit that COPR
    # did not re-build).  Check for any build matching the version instead.
    RPM_PATTERN="python3-avocado-${VERSION}-*.fc${DISTRO_VERSION}"
    echo "Checking for any COPR build matching: ${RPM_PATTERN}"
    DNF_CMD="dnf list available ${RPM_PATTERN}"
fi

# Retry loop: COPR builds may not be available immediately after a push.
# Wait up to 120 minutes (retrying every 5 minutes) for the package to appear.
MAX_WAIT_MINUTES=120
RETRY_INTERVAL_SECONDS=300
MAX_WAIT_SECONDS=$((MAX_WAIT_MINUTES * 60))
ELAPSED=0

while true; do
    if $PODMAN run --rm $PODMAN_IMAGE /bin/bash -c "${DNF_CMD}"; then
        echo "Package for version ${VERSION} is available in COPR."
        exit 0
    fi
    ELAPSED=$((ELAPSED + RETRY_INTERVAL_SECONDS))
    if [ "$ELAPSED" -ge "$MAX_WAIT_SECONDS" ]; then
        echo "ERROR: Package for version ${VERSION} not available in COPR after ${MAX_WAIT_MINUTES} minutes."
        exit 1
    fi
    echo "Package not yet available, retrying in $((RETRY_INTERVAL_SECONDS / 60)) minutes... ($((ELAPSED / 60))/${MAX_WAIT_MINUTES} min elapsed)"
    sleep $RETRY_INTERVAL_SECONDS
done
