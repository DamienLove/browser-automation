# Automation Agent

Automation Agent provides a lightweight framework for turning natural-language
requests into concrete browser automation via the Chrome DevTools Protocol.  The
project ships with:

* A reusable Python package under `automation_agent`.
* A `BrowserController` that manages a Chromium instance exposed over the Remote
  Debugging Protocol.
* A `RuleBasedPlanner` and `ActionExecutor` that translate user intent into
  executable browser actions.
* An optional `NativeBridge` that can run allowlisted desktop applications for
  hybrid workflows.
* A CLI that can operate as a desktop helper or backend for browser extensions.

The package is designed to be extended with LLM-based planners, richer action
sets, or custom safeguards.

## Installation

```bash
pip install .
```

This installs the `automation-agent` console script.

## Usage

Dry-run the planner to see the generated actions:

```bash
automation-agent plan "open https://example.com"
```

Execute a request against a locally installed Chromium:

```bash
automation-agent run "search for calendar shortcuts" --headless
```

The CLI launches a headless browser by default. Use `--no-launch` when connecting
to an already running browser that has remote debugging enabled.

## Native bridge

The optional native bridge can be configured at runtime:

```python
from automation_agent.native_bridge.bridge import NativeBridge

bridge = NativeBridge()
bridge.register("android-studio", ["/usr/bin/android-studio"])
bridge.run("android-studio")
```

Only commands that are explicitly registered in the allowlist can be executed.
Arguments containing `--unsafe` are rejected to guard against obvious
self-escalation attempts. Users should review and harden the allowlist before
connecting the agent to untrusted instruction streams.

## Safety considerations

* Browser automation is scoped to the Chrome DevTools HTTP endpoints exposed on
  `localhost`. Avoid exposing the port to untrusted networks.
* The planner implementation is deterministic and does not perform any network
  calls. Replace it with a carefully audited LLM integration for richer
  functionality.
* The native bridge relies on allowlists; disable it entirely if desktop access
  is not required.

## Development

Install development dependencies and run the tests with:

```bash
pip install -e .[dev]
pytest
```

## Testing

Unit tests cover the rule-based planner and the high-level browser controller
calls. Run the test suite with `pytest`.

## License

MIT
