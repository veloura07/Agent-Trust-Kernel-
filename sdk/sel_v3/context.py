"""Two-phase commit context manager for SEL v3."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from sel_v3.client import SELClient


class GuardContext:
    """Context manager executing Phase-2 commit/abort validation."""

    def __init__(
        self,
        client: "SELClient",
        tool_name: str,
        args: dict[str, Any],
        cost: float,
    ) -> None:
        self.client = client
        self.tool_name = tool_name
        self.args = args
        self.cost = cost
        self.transaction_id: str = ""
        self._entered = False

    def __enter__(self) -> "GuardTransaction":
        self.transaction_id = self.client.authorize(
            self.tool_name, self.args, self.cost
        )
        self._entered = True
        return GuardTransaction(self)

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if not self._entered:
            return
        phase = "ABORTED" if exc_type is not None else "COMMITTED"
        try:
            self.client.settle(
                self.transaction_id,
                phase,
                self.tool_name,
                self.args,
                self.cost,
            )
        except Exception:
            pass


class GuardTransaction:
    """Handle returned from GuardContext for explicit commit."""

    def __init__(self, ctx: GuardContext) -> None:
        self._ctx = ctx
        self.result: Any = None

    @property
    def transaction_id(self) -> str:
        return self._ctx.transaction_id

    def commit(self, result: Any = None) -> None:
        self.result = result
