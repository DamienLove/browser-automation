"""Command line interface for the automation agent."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Iterable

from .action_executor import ActionExecutor
from .browser_controller import BrowserController


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="automation-agent", description="Browser automation agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Execute a natural language request")
    run_parser.add_argument("request", help="Natural language command to execute")
    run_parser.add_argument("--chrome-path", default="google-chrome", help="Path to the Chrome/Chromium executable")
    run_parser.add_argument("--port", type=int, default=9222, help="Remote debugging port")
    run_parser.add_argument("--headless", action="store_true", help="Launch the browser in headless mode")
    run_parser.add_argument("--no-launch", action="store_true", help="Assume the browser is already running")
    run_parser.add_argument("--dry-run", action="store_true", help="Only output the action plan without executing it")

    plan_parser = subparsers.add_parser("plan", help="Print the generated plan for a request")
    plan_parser.add_argument("request")

    return parser


def _print_iterable(iterable: Iterable[object]) -> None:
    for item in iterable:
        if isinstance(item, (dict, list)):
            print(json.dumps(item))
        else:
            print(item)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "plan":
        controller = BrowserController()
        executor = ActionExecutor(controller)
        for action in executor.execute(args.request, dry_run=True):
            print(json.dumps(action))
        return 0

    if args.command == "run":
        controller = BrowserController(chrome_path=args.chrome_path, remote_debugging_port=args.port)
        executor = ActionExecutor(controller)
        if not args.no_launch:
            controller.launch_browser(headless=args.headless)
        try:
            results = executor.stream_execution(args.request, dry_run=args.dry_run)
            _print_iterable(results)
        finally:
            if not args.no_launch and controller.is_browser_running():
                controller.terminate_browser()
        return 0

    parser.error("Unknown command")
    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
