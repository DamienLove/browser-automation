"""Planning layer that transforms natural language into browser actions."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Protocol

from .browser_controller import BrowserController


class Planner(Protocol):
    """Abstract planner interface used for dependency injection."""

    def plan(self, request: str) -> List[Dict[str, Any]]:
        ...


@dataclass
class RuleBasedPlanner:
    """Very small heuristic planner used as a deterministic baseline.

    The class is intentionally simplistic so it can run in offline test
    environments.  Projects can replace it with an LLM-backed implementation by
    providing an object that implements :class:`Planner`.
    """

    default_search_engine: str = "https://www.google.com/search?q={query}"

    def plan(self, request: str) -> List[Dict[str, Any]]:
        lowered = request.lower().strip()
        if lowered.startswith("open "):
            url = request[5:].strip()
            if not url.startswith("http"):
                url = self.default_search_engine.format(query=url.replace(" ", "+"))
            return [{"type": "open_url", "url": url}]
        if "search for" in lowered:
            query = request.split("search for", 1)[1].strip()
            url = self.default_search_engine.format(query=query.replace(" ", "+"))
            return [{"type": "open_url", "url": url}]
        return [{"type": "open_url", "url": self.default_search_engine.format(query=request.replace(" ", "+"))}]


class ActionExecutor:
    """Coordinates planning and browser control."""

    def __init__(self, browser_controller: BrowserController, planner: Planner | None = None) -> None:
        self.browser_controller = browser_controller
        self.planner = planner or RuleBasedPlanner()

    def execute(self, request: str, *, dry_run: bool = False) -> List[Dict[str, Any]]:
        plan = self.planner.plan(request)
        if dry_run:
            return plan
        return self.browser_controller.perform_actions(plan)

    def stream_execution(self, request: str, *, dry_run: bool = False) -> Iterable[Dict[str, Any]]:
        plan = self.planner.plan(request)
        if dry_run:
            for action in plan:
                yield action
            return
        for action in plan:
            yield self.browser_controller.execute_action(action)


__all__ = ["ActionExecutor", "RuleBasedPlanner", "Planner"]
