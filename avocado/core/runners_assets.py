import json

# pylint: disable=W4901
from distutils.errors import DistutilsSetupError


def check_runners_assets(dist, attr, value):  # pylint: disable=W0613
    if not isinstance(value, dict):
        raise DistutilsSetupError(
            "runners_assets must be a dictionary keyed by test kind"
        )

    for kind, entries in value.items():
        if not isinstance(entries, list):
            raise DistutilsSetupError(f"value for runners_assets {kind} must be a list")
        for entry in entries:
            if not ("url_format" in entry or "url" in entry):
                raise DistutilsSetupError(
                    f'asset for runner {kind} lacks "url" or "url_format"'
                )
            if "url_format" in entry and "url" in entry:
                raise DistutilsSetupError(
                    f'asset for runner {kind} has conflicting options "url" and "url_format", only one is allowed'
                )
            if not "type" in entry:
                raise DistutilsSetupError(f'asset for runner {kind} lacks "type"')


def write_runners_assets_json(cmd, basename, filename):  # pylint: disable=W0613
    if (
        not hasattr(cmd.distribution, "runners_assets")
        or not cmd.distribution.runners_assets
    ):
        return
    cmd.write_file(
        "runners_assets",
        filename,
        json.dumps(cmd.distribution.runners_assets, sort_keys=True),
    )
