"""
MAF logging middleware.

Plugs into the agent-framework middleware chain to emit structured
timing / tool-call logs, and populates the agent trace panel in
the Zava UI (via the event_queue channel used by SSE routes).
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, Optional

from agent_framework import Message
from agent_framework.middleware import MiddlewareBase


class LoggingMiddleware(MiddlewareBase):
    """
    Logs each agent invocation with timing and surfaced tool names.

    Attach once at the workflow level so all agents in the pipeline
    share the same middleware instance.

    Usage::

        client = get_maf_client(
            middleware=[LoggingMiddleware(event_queue=my_queue)]
        )
    """

    def __init__(
        self,
        *,
        event_queue: Optional[Any] = None,
        agent_name: str = "agent",
    ) -> None:
        self._event_queue = event_queue
        self._agent_name = agent_name

    # ------------------------------------------------------------------
    # MiddlewareBase contract
    # ------------------------------------------------------------------

    async def on_agent_start(
        self,
        messages: list[Message],
        *,
        next_handler: Callable,
        **kwargs: Any,
    ) -> Any:
        start = time.monotonic()
        self._emit("start", {"agent": self._agent_name, "input_length": len(messages)})

        result = await next_handler(messages, **kwargs)

        elapsed = round((time.monotonic() - start) * 1000)
        tools = self._extract_tool_names(result)
        self._emit(
            "complete",
            {"agent": self._agent_name, "elapsed_ms": elapsed, "tools_used": tools},
        )
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _emit(self, event: str, payload: Dict[str, Any]) -> None:
        import json

        data = json.dumps({"event": event, **payload})
        print(f"[MAF] {data}")

        if self._event_queue:
            try:
                self._event_queue.put_nowait({"type": "agent_event", "data": data})
            except Exception:
                pass  # Non-blocking — never crash an agent run over logging

    @staticmethod
    def _extract_tool_names(result: Any) -> list[str]:
        """Pull tool names from a list[Message] or a single Message."""
        names: list[str] = []
        messages = result if isinstance(result, list) else [result]
        for msg in messages:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    name = getattr(getattr(tc, "function", None), "name", None)
                    if name:
                        names.append(name)
        return names
