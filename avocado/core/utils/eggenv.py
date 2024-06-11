import os
from importlib import metadata


def get_python_path_env_if_egg():
    """
    Returns an environment mapping with an extra PYTHONPATH for the egg or None

    When running Avocado Python modules, the interpreter on the new
    process needs to know where Avocado can be found.  This is usually
    handled by the Avocado installation being available to the
    standard Python installation, but if Avocado is running from an
    uninstalled egg, it needs extra help.

    :returns: environment mapping with an extra PYTHONPATH for the egg or None
    :rtype: os.environ mapping or None
    """
    dist_location = metadata.distribution("avocado-framework").locate_file("")
    if not (str(dist_location).endswith(".egg") and dist_location.is_file()):
        return None

    python_path = os.environ.get("PYTHONPATH", "")
    python_path_entries = python_path.split(":")
    if dist_location in python_path_entries:
        return None

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{dist_location}:{python_path}"
    return env
