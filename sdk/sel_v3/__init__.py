"""SEL v3 Python Client SDK — zero-dependency agent trust kernel."""

from sel_v3.client import SELClient, SELBlockedError, SELAuthorizationError
from sel_v3.decorator import sel_guard
from sel_v3.context import GuardTransaction

__all__ = [
    "SELClient",
    "SELBlockedError",
    "SELAuthorizationError",
    "sel_guard",
    "GuardTransaction",
]

__version__ = "3.0.0"
