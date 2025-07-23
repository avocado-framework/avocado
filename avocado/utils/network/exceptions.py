"""Exception hierarchy for network utilities.

This module defines custom exception classes used throughout network utilities.
All specific network errors should inherit from :class:`NWException` so they can
be handled collectively when required.
"""


class NWException(Exception):
    """Base Exception Class for all network utility exceptions."""
