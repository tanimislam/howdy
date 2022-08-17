"""
Copying over `deluge-client <https://github.com/JohnDoee/deluge-client>`_, instead of creating a special branch, because I had to modify the ``DelugeRPCClient`` object code due to *much stricter* SSL security policies in Python 3.10.
"""

from .client import (
    DelugeRPCClient, LocalDelugeRPCClient, FailedToReconnectException
)
