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
# Copyright: Red Hat Inc. 2026
"""Bootstrap Avocado into isolated environments from a universal wheel.

Python eggs are a discontinued format: they are CPython-minor specific,
need pkg_resources (removed in setuptools 82), and already fail inside
Fedora 39+ containers. Avocado is pure Python, so one
``avocado_framework-{version}-py3-none-any.whl`` works for every
supported interpreter.

The wheel is unpacked once on the host (stdlib zipfile) and bind-mounted
read-only. nrunner then uses ``python -m avocado.plugins.runners...``,
so console scripts and a venv are unnecessary.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse

from avocado.core.version import VERSION
from avocado.utils.asset import Asset

LOG = logging.getLogger(__name__)

#: Where the unpacked wheel (or a legacy egg file) is visible inside
#: the isolated environment.
CONTAINER_SITE = "/opt/avocado-wheel"
_EXTRACT_MARKER = ".avocado-wheel-extracted"


@dataclass(frozen=True)
class BootstrapMount:
    """Host path to bind-mount and the PYTHONPATH to use inside."""

    host_path: str
    container_path: str
    pythonpath: str


def source_root():
    """Return the Avocado git/source tree if this checkout has one."""
    # avocado/core/spawners/wheel_bootstrap.py -> repository root
    repo = Path(__file__).resolve().parents[3]
    if (repo / "setup.py").exists() and (repo / "VERSION").exists():
        return repo
    return None


def effective_version(version=None):
    """Installed package version, or VERSION file when running from git."""
    if version is None:
        version = VERSION
    if version != "unknown.unknown":
        return version
    src = source_root()
    if src is not None:
        return (src / "VERSION").read_text(encoding="utf-8").strip()
    return version


def wheel_filename(version=None):
    """Return the universal wheel filename for an Avocado version."""
    return f"avocado_framework-{effective_version(version)}-py3-none-any.whl"


def default_wheel_url(version=None):
    """GitHub release URL for the universal wheel."""
    version = effective_version(version)
    name = wheel_filename(version)
    return (
        f"https://github.com/avocado-framework/avocado/releases/"
        f"download/{version}/{name}"
    )


def _local_path_from_url(url):
    parsed = urlparse(url)
    if parsed.scheme in ("", "file"):
        path = unquote(parsed.path)
        if parsed.netloc and parsed.netloc != "localhost":
            path = f"/{parsed.netloc}{path}"
        return path
    return None


def _extract_wheel(wheel_path, dest_dir):
    dest = Path(dest_dir)
    marker = dest / _EXTRACT_MARKER
    wheel_path = os.path.abspath(wheel_path)
    if marker.exists() and marker.read_text(encoding="utf-8").strip() == wheel_path:
        return str(dest)
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    with zipfile.ZipFile(wheel_path) as archive:
        archive.extractall(dest)
    marker.write_text(wheel_path, encoding="utf-8")
    return str(dest)


def _pip_output(result, what):
    if result.returncode != 0:
        raise RuntimeError(
            f"{what} failed with exit {result.returncode}:\n"
            f"{result.stdout.decode(errors='replace')}"
        )


_COPYTREE_IGNORE = shutil.ignore_patterns(
    ".git",
    ".github",
    "docs",
    "selftests",
    "PYPI_UPLOAD",
    "EGG_UPLOAD",
    "build",
    "dist",
    "*.egg-info",
    "__pycache__",
)


def _copy_regular(source, work, name):
    """Copy ``name`` as a real file.

    ``README.rst`` is a symlink into ``docs/``.  ``git archive`` keeps
    that symlink, and the copytree fallback omits ``docs/``, so
    ``setup.py`` would otherwise fail to open it.
    """
    src = Path(source) / name
    dest = Path(work) / name
    if not src.exists():
        return
    if dest.exists() or dest.is_symlink():
        dest.unlink()
    shutil.copyfile(src, dest)


def _snapshot_source(source):
    """Return a writable copy of ``source`` that pip wheel can mutate.

    Prefer ``git archive`` so a live checkout being used by parallel
    selftests is not read mid-write.  Fall back to copytree.
    """
    source = Path(source)
    git_src = str(source.resolve())
    tmp = Path(tempfile.mkdtemp(prefix="avocado-wheel-src-"))
    work = tmp / "src"
    work.mkdir()
    archived = False
    if (source / ".git").exists():
        try:
            archive = subprocess.run(
                [
                    "git",
                    "-C",
                    git_src,
                    "-c",
                    f"safe.directory={git_src}",
                    "archive",
                    "--format=tar",
                    "HEAD",
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            subprocess.run(
                ["tar", "-x", "-C", str(work)],
                check=True,
                input=archive.stdout,
            )
            archived = True
        except (OSError, subprocess.CalledProcessError) as exc:
            LOG.debug("git archive of %s failed (%s); copying the tree", source, exc)
            shutil.rmtree(work)
    if not archived:
        shutil.copytree(
            source,
            work,
            symlinks=True,
            ignore=_COPYTREE_IGNORE,
            dirs_exist_ok=True,
        )
    _copy_regular(source, work, "README.rst")
    return tmp, work


def build_wheel_from_source(source, dest_dir):
    """Build a universal wheel from a source tree with pip.

    The tree is snapshotted first.  setuptools writes ``*.egg-info``
    during the build, and parallel selftests can mutate a live checkout.

    :param source: path to the Avocado repository
    :param dest_dir: directory that will receive the ``.whl``
    :returns: path to the built wheel
    """
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    tmp, work = _snapshot_source(source)
    try:
        LOG.info("Building Avocado wheel from %s", work)
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "wheel",
                "--no-deps",
                "-w",
                str(dest),
                str(work),
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        _pip_output(result, "pip wheel")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    wheels = sorted(dest.glob("avocado_framework-*.whl"))
    if not wheels:
        raise RuntimeError(f"pip wheel produced no avocado_framework wheel in {dest}")
    return str(wheels[-1])


def download_pypi_wheel(version, dest_dir):
    """Download the universal Avocado wheel from PyPI."""
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    requirement = f"avocado-framework=={effective_version(version)}"
    LOG.info("Downloading %s from PyPI", requirement)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "download",
            "--no-deps",
            "--only-binary=:all:",
            "-d",
            str(dest),
            requirement,
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    _pip_output(result, f"pip download {requirement}")
    wheels = sorted(dest.glob("avocado_framework-*.whl"))
    if not wheels:
        raise RuntimeError(
            f"pip download produced no avocado_framework wheel in {dest}"
        )
    return str(wheels[-1])


def _fetch_remote_wheel(url, cache_dirs):
    asset = Asset(url, cache_dirs=cache_dirs)
    return asset.fetch()


def resolve_wheel_file(url=None, cache_dirs=None, version=None):
    """Return a local path to an Avocado wheel (or legacy egg).

    Resolution order:

    1. Explicit URL (``file://`` or remote).
    2. Wheel built from the source tree this module lives in (develop).
    3. GitHub release asset for ``version``.
    4. PyPI ``avocado-framework==version`` (covers releases that still
       only uploaded eggs to GitHub).
    """
    if version is None:
        version = effective_version()
    if cache_dirs is None:
        cache_dirs = []
    cache_root = Path(cache_dirs[0] if cache_dirs else Path.cwd()) / "wheel-bootstrap"
    cache_root.mkdir(parents=True, exist_ok=True)

    if url:
        local = _local_path_from_url(url)
        if local:
            if not os.path.exists(local):
                raise FileNotFoundError(f"Bootstrap package not found: {local}")
            return local
        return _fetch_remote_wheel(url, cache_dirs)

    src = source_root()
    if src is not None:
        built = cache_root / wheel_filename(version)
        if built.exists():
            return str(built)
        return build_wheel_from_source(src, cache_root)

    try:
        return _fetch_remote_wheel(default_wheel_url(version), cache_dirs)
    except OSError as exc:
        LOG.warning(
            "GitHub wheel for Avocado %s is not available (%s); trying PyPI",
            version,
            exc,
        )
        return download_pypi_wheel(version, cache_root)


def prepare_bootstrap(url=None, cache_dirs=None, version=None):
    """Prepare a host directory or file to mount into an isolated environment.

    Wheels are unpacked so ``import avocado`` works via PYTHONPATH.
    Legacy ``.egg`` files are returned as-is (zipimport) with a warning.
    """
    package = resolve_wheel_file(url=url, cache_dirs=cache_dirs, version=version)
    if package.endswith(".egg"):
        LOG.warning(
            "Egg bootstrap is deprecated and fails on Fedora 39+/Python "
            "3.12+. Pass a universal wheel instead (%s).",
            wheel_filename(version),
        )
        container = os.path.join(CONTAINER_SITE, os.path.basename(package))
        return BootstrapMount(
            host_path=os.path.abspath(package),
            container_path=container,
            pythonpath=container,
        )

    if os.path.isdir(package):
        host_dir = os.path.abspath(package)
    else:
        cache_root = (
            Path(cache_dirs[0] if cache_dirs else Path.cwd()) / "wheel-bootstrap"
        )
        host_dir = _extract_wheel(package, cache_root / "site")

    return BootstrapMount(
        host_path=host_dir,
        container_path=CONTAINER_SITE,
        pythonpath=CONTAINER_SITE,
    )
