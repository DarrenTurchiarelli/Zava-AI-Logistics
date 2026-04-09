"""
MAF logging middleware.

Plugs into the agent-framework middleware chain to emit structured
timing / tool-call logs, and populates the agent trace panel in
the Zava UI (via the event_queue channel used by SSE routes).
"""

from __future__ import annotations

import json
import time
from typing import Any, Optional

from agent_framework import AgentContext, AgentMiddleware


class LoggingMiddleware(AgentMiddleware):
    """
    Logs each agent invocation with timing and surfaced tool names.

    Attach at the client level so all agents in the pipeline share
    the same middleware instance.

    Usage::

        from agent_framework.azure import AzureAIClient
        client = AzureAIClient(
            ...,
            middleware=[LoggingMiddleware(event_queue=my_queue)],
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
    # AgentMiddleware contract
    # ------------------------------------------------------------------

    async def process(self, context: AgentContext, call_next) -> None:
        start = time.monotonic()
        name = getattr(context.agent, "name", self._agent_name)
        self._emit("start", {"agent": name, "input_length": len(context.messages)})

        await call_next()

        elapsed = round((time.monotonic() - start) * 1000)
        self._emit("complete", {"agent": name, "elapsed_ms": elapsed})

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _emit(self, event: str, payload: dict) -> None:
        data = json.dumps({"event": event, **payload})
        print(f"[MAF] {data}")

        if self._event_queue:
            try:
                self._event_queue.put_nowait({"type": "agent_event", "data": data})
            except Exception:
                pass  # Non-blocking — never crash an agent run over logging

