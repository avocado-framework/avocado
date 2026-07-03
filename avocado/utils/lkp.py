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
# Copyright: 2026 Advanced Micro Devices, Inc.
# Author: Sumit Kumar <sumitkum@amd.com>

"""
Framework-independent helpers to drive Intel LKP (lkp-tests) microbenchmarks.
The public surface is :func:`clone`, :func:`install`, :func:`install_job`,
:func:`run_job`, :func:`find_result_file` and :func:`archive_results`. Package
installation and result assertions belong in the test that uses them.
"""

import glob
import logging
import os
import re
import shlex
import shutil

from avocado.utils import git, process

LOG = logging.getLogger(__name__)

_SPLIT_RE = re.compile(r"=>\s*\./(?P<name>\S+\.yaml)\s*$")
_INSTALL_TIMEOUT = 1800

#: Drop-in apt installer for lkp-tests: the stock one aborts when any package
#: in lkp's dependency list has no install candidate (newer releases drop
#: legacy names like ``libaio1``); this one installs only what apt resolves.
_TOLERANT_APT_INSTALLER = r"""#!/bin/sh
available=
for pkg in "$@"; do
	cand=$(LC_ALL=C apt-cache policy "$pkg" 2>/dev/null | sed -n 's/^  Candidate: //p')
	[ -n "$cand" ] && [ "$cand" != "(none)" ] && available="$available $pkg"
done
[ -n "$available" ] || exit 0
# shellcheck disable=SC2086
DEBIAN_FRONTEND=noninteractive apt-get -y install $available
"""


def _make_installer_tolerant(lkp_dir):
    """Make the cloned lkp-tests apt installer skip unavailable packages."""
    for distro in ("ubuntu", "debian"):
        path = os.path.join(lkp_dir, "distro", "installer", distro)
        if not os.path.isfile(path):
            continue
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(_TOLERANT_APT_INSTALLER)
        os.chmod(path, 0o755)


def _run(cmd, cwd, sudo=False, ignore_status=False, timeout=None,
         env=None, auto_answer=False):
    """
    Compose and run a single shell command from ``cwd``.

    The command is composed as ``cd <cwd> [&& export ...] && [yes |] <cmd>``
    and run via :func:`process.run` with ``shell=True``.

    :param cmd: the command to run (already quoted as needed).
    :param cwd: directory to ``cd`` into before running ``cmd``.
    :param sudo: run the composed command with elevated privileges.
    :param ignore_status: when True, do not raise on a non-zero exit status;
                          the caller inspects :attr:`CmdResult.exit_status`.
    :param timeout: timeout in seconds passed through to :func:`process.run`.
    :param env: optional mapping of environment variables.
    :param auto_answer: when True, pipe ``yes`` into the command to answer
                        interactive prompts. Use this only for steps that
                        are known to prompt (package install / build), never
                        for long-running benchmark runs which would otherwise
                        receive an endless stdin stream and may hang.
    :returns: the :class:`process.CmdResult` of the run.
    """
    parts = ["cd %s" % shlex.quote(cwd)]
    if env:
        # Export inside the shell, not via process.run(env=...), so the vars
        # survive the ``sudo`` wrapper and reach every stage of the pipeline.
        exports = " ".join(
            "%s=%s" % (key, shlex.quote(str(val))) for key, val in env.items()
        )
        parts.append("export %s" % exports)
    parts.append(("yes | %s" % cmd) if auto_answer else cmd)
    full = " && ".join(parts)
    # process.run(sudo=True) only prepends ``sudo`` to the first token, so with
    # a ``cd ... && ...`` pipeline only the ``cd`` would be privileged. Wrap the
    # whole pipeline in ``sudo -n sh -c`` so every stage runs elevated.
    if sudo and hasattr(os, "getuid") and os.getuid() != 0:
        full = "sudo -n sh -c %s" % shlex.quote(full)
        sudo = False
    return process.run(full, shell=True, sudo=sudo,
                       ignore_status=ignore_status, timeout=timeout)


def _ensure_testbox(lkp_dir, testbox):
    """Create a minimal ``hosts/<testbox>`` description if absent."""
    host = os.path.join(lkp_dir, "hosts", testbox)
    if os.path.isfile(host):
        return
    os.makedirs(os.path.dirname(host), exist_ok=True)
    with open(host, "w", encoding="utf-8") as handle:
        handle.write("nr_cpu: %d\n" % (os.cpu_count() or 1))


def clone(uri, dest, branch="master"):
    """
    Clone (or reuse) the lkp-tests repository at ``dest``.

    :param uri: git URL of the lkp-tests repository.
    :param dest: destination directory for the checkout.
    :param branch: remote branch to fetch.
    :returns: the absolute path of the checkout.
    """
    dest = os.path.abspath(dest)
    if os.path.isdir(os.path.join(dest, ".git")):
        LOG.debug("Reusing existing lkp-tests checkout at %s", dest)
        return dest
    git.get_repo(uri, branch=branch, destination_dir=dest)
    return dest


def install(lkp_dir, sudo=True, extra=None):
    """
    Build the lkp-tests subsystem and run the base ``bin/lkp install``.

    The build and install steps may prompt (package managers, account
    creation), so ``yes`` is piped only into those steps. The per-step
    timeout is the module-level :data:`_INSTALL_TIMEOUT`.

    :param lkp_dir: path to the lkp-tests checkout.
    :param sudo: run the install steps with elevated privileges.
    :param extra: extra arguments appended to ``bin/lkp install`` (e.g.
                  ``"--skip-base"``). Applies to this base install only.
    :returns: the absolute path of the ``bin/lkp`` executable.
    """
    lkp_dir = os.path.abspath(lkp_dir)
    _make_installer_tolerant(lkp_dir)
    build_env = {"DEBIAN_FRONTEND": "noninteractive"}
    _run("make -j1 subsystem", lkp_dir, sudo=sudo, timeout=_INSTALL_TIMEOUT,
         env=build_env, auto_answer=True)
    _run("make -j1 install", lkp_dir, sudo=sudo, timeout=_INSTALL_TIMEOUT,
         env=build_env, auto_answer=True)

    lkp_bin = os.path.join(lkp_dir, "bin", "lkp")
    cmd = "%s install" % shlex.quote(lkp_bin)
    if extra:
        cmd += " " + extra
    _run(cmd, lkp_dir, sudo=sudo, timeout=_INSTALL_TIMEOUT, env=build_env,
         auto_answer=True)
    return lkp_bin


def install_job(lkp_dir, job_yaml, testbox, sudo=True):
    """
    Split a job YAML into concrete sub-jobs and install their dependencies.

    A minimal ``hosts/<testbox>`` description is created if missing, then
    ``lkp split-job`` is run (no auto-answer) and its ``=> ./<name>.yaml``
    lines are parsed into sub-job paths relative to ``lkp_dir``. For each
    sub-job ``bin/lkp install <sub>`` is run (with ``yes`` auto-answer) to
    pull the per-benchmark dependencies. The per-step timeout is the
    module-level :data:`_INSTALL_TIMEOUT`.

    :param lkp_dir: path to the lkp-tests checkout.
    :param job_yaml: path to the staged job YAML to split.
    :param testbox: testbox name used by ``lkp split-job -t``.
    :param sudo: run the per-sub-job dependency install with elevated
                 privileges (package installation usually needs root).
    :returns: list of absolute paths to the generated sub-job YAML files.
    :raises RuntimeError: if ``lkp split-job`` produces no sub-jobs.
    """
    lkp_dir = os.path.abspath(lkp_dir)
    lkp_bin = os.path.join(lkp_dir, "bin", "lkp")
    _ensure_testbox(lkp_dir, testbox)

    cmd = "%s split-job -t %s %s" % (
        shlex.quote(lkp_bin), shlex.quote(testbox), shlex.quote(job_yaml))
    result = _run(cmd, lkp_dir, timeout=_INSTALL_TIMEOUT)

    output = "%s\n%s" % (result.stdout_text or "", result.stderr_text or "")
    subs = []
    for line in output.splitlines():
        match = _SPLIT_RE.search(line)
        if not match:
            continue
        path = os.path.join(lkp_dir, match.group("name"))
        if os.path.isfile(path):
            subs.append(os.path.abspath(path))
    if not subs:
        raise RuntimeError(
            "lkp split-job produced no sub-jobs for %s" % job_yaml)

    for sub in subs:
        cmd = "%s install %s" % (
            shlex.quote(lkp_bin), shlex.quote(os.path.basename(sub)))
        _run(cmd, os.path.dirname(sub), sudo=sudo, timeout=_INSTALL_TIMEOUT,
             env={"DEBIAN_FRONTEND": "noninteractive"}, auto_answer=True)
    return subs


def run_job(lkp_dir, sub_job, timeout=3600):
    """
    Run a single lkp-tests sub-job locally.

    The benchmark must never receive an interactive ``yes`` stream, so this
    step is run without auto-answer. ``ignore_status`` is set so the caller
    can inspect the exit status and the produced result files even when LKP
    returns non-zero (a finished non-zero run is detectable, not a hang).

    :param lkp_dir: path to the lkp-tests checkout.
    :param sub_job: path to a concrete sub-job YAML produced by
                    :func:`install_job`.
    :param timeout: timeout in seconds. Must be larger than the benchmark's
                    own runtime (``testtime``) so the run is not killed early.
    :returns: the :class:`process.CmdResult` of the run.
    """
    lkp_dir = os.path.abspath(lkp_dir)
    lkp_bin = os.path.join(lkp_dir, "bin", "lkp")
    sub_job = os.path.abspath(sub_job)
    cwd = os.path.dirname(sub_job)

    run_env = {
        "BENCHMARK_ROOT": os.path.join(lkp_dir, "benchmarks"),
        "LKP_LOCAL_RUN": "1",
    }
    cmd = "%s run %s" % (shlex.quote(lkp_bin),
                         shlex.quote(os.path.basename(sub_job)))
    return _run(cmd, cwd, ignore_status=True, timeout=timeout, env=run_env)


def find_result_file(root, name):
    """
    Return the newest ``name`` found recursively under ``root``.

    :param root: directory to search under (typically the lkp-tests checkout).
    :param name: result file name to look for, e.g. ``"mpstat.json"``.
    :returns: the absolute path of the newest match, or ``None`` if not found.
    """
    if not root or not os.path.isdir(root):
        return None
    matches = glob.glob(os.path.join(root, "**", name), recursive=True)

    def safe_getmtime(path):
        # Files may vanish or be broken symlinks between glob and sort; treat
        # those as oldest instead of letting os.path.getmtime raise OSError.
        try:
            return os.path.getmtime(path)
        except OSError:
            return 0

    matches = sorted(set(matches), key=safe_getmtime)
    return matches[-1] if matches else None


def archive_results(lkp_dir, result_name, dest):
    """
    Copy the lkp result directory containing ``result_name`` into ``dest``.

    The lkp checkout usually lives under a test's working directory, which the
    framework removes once the test finishes; copying the result directory to a
    persistent location keeps the artifacts available after the run.

    :param lkp_dir: path to the lkp-tests checkout to search for results.
    :param result_name: result file name used to locate the result directory,
                        e.g. ``"mpstat.json"`` or ``"stats.json"``.
    :param dest: destination directory; replaced if it already exists.
    :returns: the destination path on success, or ``None`` when no result file
              was found or the copy failed.
    """
    result_file = find_result_file(lkp_dir, result_name)
    if not result_file:
        LOG.warning("No lkp result file found to archive.")
        return None
    result_dir = os.path.dirname(result_file)
    try:
        if os.path.isdir(dest) and not os.path.islink(dest):
            shutil.rmtree(dest)
        elif os.path.exists(dest) or os.path.islink(dest):
            os.remove(dest)
        shutil.copytree(result_dir, dest)
        LOG.info("Archived lkp results from %s to %s", result_dir, dest)
        return dest
    except (OSError, shutil.Error) as err:
        LOG.warning("Failed to archive lkp results: %s", err)
        return None
