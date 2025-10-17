"""Browser control utilities built on top of the Chrome DevTools Protocol.

The implementation focuses on providing a minimal-yet-safe interface for
launching a Chromium based browser with the remote debugging port enabled and
issuing high level commands for common automation tasks.  The code is written so
that network and process interactions can be stubbed in tests.
"""
from __future__ import annotations

import json
import subprocess
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional


class HTTPError(RuntimeError):
    """Raised when the DevTools HTTP endpoint returns an unexpected response."""


@dataclass
class _ProcessHandle:
    popen: subprocess.Popen

    def terminate(self) -> None:
        if self.popen.poll() is None:
            self.popen.terminate()

    def wait(self, timeout: Optional[float] = None) -> Optional[int]:
        try:
            return self.popen.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            return None

    def is_running(self) -> bool:
        return self.popen.poll() is None


class _DefaultHTTPClient:
    """Small wrapper around :mod:`urllib` so the implementation can be mocked."""

    def request(self, url: str, *, data: Optional[bytes] = None, method: str = "GET") -> bytes:
        req = urllib.request.Request(url, data=data, method=method)
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                return response.read()
        except Exception as exc:  # pragma: no cover - urllib generates varying errors
            raise HTTPError(f"DevTools endpoint request failed for {url}: {exc}") from exc


class BrowserController:
    """Launches a Chromium browser and executes DevTools commands."""

    def __init__(
        self,
        chrome_path: str = "google-chrome",
        remote_debugging_port: int = 9222,
        host: str = "127.0.0.1",
        startup_timeout: float = 15.0,
        http_client: Optional[_DefaultHTTPClient] = None,
        process_factory: Optional[Callable[[List[str]], subprocess.Popen]] = None,
    ) -> None:
        self.chrome_path = chrome_path
        self.remote_debugging_port = remote_debugging_port
        self.host = host
        self.startup_timeout = startup_timeout
        self._http_client = http_client or _DefaultHTTPClient()
        self._process_factory = process_factory or subprocess.Popen
        self._process: Optional[_ProcessHandle] = None

    # ------------------------------------------------------------------
    # Process lifecycle helpers
    # ------------------------------------------------------------------
    def launch_browser(self, *, headless: bool = True, user_data_dir: Optional[str] = None, additional_args: Optional[Iterable[str]] = None) -> None:
        """Starts the browser with remote debugging enabled.

        The method returns immediately once the browser process is spawned.  A
        health check is performed to ensure the remote debugging endpoint is
        reachable.
        """

        if self._process and self._process.is_running():
            return

        args = [
            self.chrome_path,
            f"--remote-debugging-port={self.remote_debugging_port}",
            "--remote-allow-origins=*",
        ]
        if headless:
            args.append("--headless=new")
        if user_data_dir:
            args.append(f"--user-data-dir={user_data_dir}")
        if additional_args:
            args.extend(additional_args)

        popen = self._process_factory(args)
        self._process = _ProcessHandle(popen=popen)
        self._wait_until_ready()

    def is_browser_running(self) -> bool:
        return bool(self._process and self._process.is_running())

    def terminate_browser(self) -> None:
        if self._process:
            self._process.terminate()
            self._process.wait(timeout=5)
            self._process = None

    # ------------------------------------------------------------------
    # DevTools helpers
    # ------------------------------------------------------------------
    def list_tabs(self) -> List[Dict[str, Any]]:
        payload = self._request("/json/list")
        return json.loads(payload.decode("utf-8"))

    def open_tab(self, url: str) -> Dict[str, Any]:
        query = urllib.parse.urlencode({"url": url})
        payload = self._request(f"/json/new?{query}")
        return json.loads(payload.decode("utf-8"))

    def close_tab(self, target_id: str) -> Dict[str, Any]:
        payload = self._request(f"/json/close/{target_id}")
        return json.loads(payload.decode("utf-8"))

    def activate_tab(self, target_id: str) -> Dict[str, Any]:
        payload = self._request(f"/json/activate/{target_id}")
        return json.loads(payload.decode("utf-8"))

    def execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Executes a high-level action.

        Supported action types:
        - ``open_url``: opens the URL in a new tab.
        - ``activate``: activates an existing tab.
        - ``close``: closes an existing tab.
        """

        action_type = action.get("type")
        if action_type == "open_url":
            url = action.get("url")
            if not url:
                raise ValueError("open_url action requires a 'url'")
            return self.open_tab(url)
        if action_type == "activate":
            target_id = action.get("target_id")
            if not target_id:
                raise ValueError("activate action requires a 'target_id'")
            return self.activate_tab(target_id)
        if action_type == "close":
            target_id = action.get("target_id")
            if not target_id:
                raise ValueError("close action requires a 'target_id'")
            return self.close_tab(target_id)
        raise ValueError(f"Unsupported action type: {action_type}")

    def perform_actions(self, actions: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []
        for action in actions:
            results.append(self.execute_action(action))
        return results

    # ------------------------------------------------------------------
    # Internal utilities
    # ------------------------------------------------------------------
    def _wait_until_ready(self) -> None:
        """Polls the remote debugging endpoint until it responds or times out."""

        deadline = time.time() + self.startup_timeout
        last_error: Optional[Exception] = None
        while time.time() < deadline:
            try:
                self.list_tabs()
                return
            except Exception as exc:  # pragma: no cover - exercised implicitly
                last_error = exc
                time.sleep(0.5)
        raise TimeoutError("Browser did not become ready in time") from last_error

    def _request(self, path: str) -> bytes:
        url = f"http://{self.host}:{self.remote_debugging_port}{path}"
        return self._http_client.request(url)


__all__ = ["BrowserController", "HTTPError"]
