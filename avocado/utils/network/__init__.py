import warnings

from .ports import PortTracker  # noqa pylint: disable=unused-import
from .ports import find_free_port  # noqa pylint: disable=unused-import
from .ports import find_free_ports  # noqa pylint: disable=unused-import
from .ports import is_port_free  # noqa pylint: disable=unused-import

warnings.warn(("Network as module will be deprecated, please use "
               "utils.network.ports instead."),
              DeprecationWarning,
              stacklevel=2)
