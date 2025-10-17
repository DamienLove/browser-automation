import json
from typing import List

import pytest

from automation_agent.browser_controller import BrowserController


class FakeProcess:
    def __init__(self):
        self.terminated = False

    def poll(self):
        return None if not self.terminated else 0

    def wait(self, timeout=None):
        self.terminated = True
        return 0

    def terminate(self):
        self.terminated = True


class FakeHTTPClient:
    def __init__(self):
        self.requests: List[str] = []

    def request(self, url: str, data=None, method="GET") -> bytes:
        self.requests.append(url)
        if url.endswith("/json/list"):
            return b"[]"
        if "/json/new" in url:
            return json.dumps({"id": "target-1"}).encode("utf-8")
        if "/json/close" in url or "/json/activate" in url:
            return json.dumps({"status": "ok"}).encode("utf-8")
        raise AssertionError(f"Unexpected URL {url}")


@pytest.fixture
def controller():
    http_client = FakeHTTPClient()
    process = FakeProcess()
    controller = BrowserController(
        chrome_path="/usr/bin/chrome",
        remote_debugging_port=9333,
        http_client=http_client,
        process_factory=lambda args: process,
    )
    controller._wait_until_ready = lambda: None  # type: ignore[attr-defined]
    controller._fake_process = process  # type: ignore[attr-defined]
    controller._fake_http_client = http_client  # type: ignore[attr-defined]
    return controller


def test_open_tab_uses_remote_debugging_endpoint(controller):
    result = controller.open_tab("https://example.com")
    assert result["id"] == "target-1"
    expected_url = "http://127.0.0.1:9333/json/new?url=https%3A%2F%2Fexample.com"
    assert controller._fake_http_client.requests[-1] == expected_url


def test_perform_actions_invokes_individual_actions(controller):
    actions = [
        {"type": "open_url", "url": "https://example.com"},
        {"type": "activate", "target_id": "target-1"},
        {"type": "close", "target_id": "target-1"},
    ]
    results = controller.perform_actions(actions)
    assert len(results) == 3
    assert controller._fake_http_client.requests[-1].endswith("/json/close/target-1")


def test_launch_browser_invokes_process_factory():
    http_client = FakeHTTPClient()
    process = FakeProcess()
    calls = []

    def process_factory(args):
        calls.append(args)
        return process

    controller = BrowserController(
        chrome_path="/usr/bin/chrome",
        remote_debugging_port=9333,
        http_client=http_client,
        process_factory=process_factory,
    )

    controller._wait_until_ready = lambda: None  # type: ignore[attr-defined]
    controller.launch_browser(headless=True)

    assert calls
    assert calls[0][0] == "/usr/bin/chrome"
    assert any(arg.startswith("--remote-debugging-port=9333") for arg in calls[0])
