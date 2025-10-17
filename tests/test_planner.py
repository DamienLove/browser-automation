from automation_agent.action_executor import ActionExecutor, RuleBasedPlanner


class DummyController:
    def __init__(self):
        self.actions = []

    def perform_actions(self, actions):
        self.actions.extend(actions)
        return [{"result": "ok"} for _ in actions]


def test_rule_based_planner_open_url():
    planner = RuleBasedPlanner()
    actions = planner.plan("open https://example.com")
    assert actions == [{"type": "open_url", "url": "https://example.com"}]


def test_action_executor_dry_run_returns_plan():
    controller = DummyController()
    executor = ActionExecutor(controller)
    plan = executor.execute("search for testing shortcuts", dry_run=True)
    assert plan
    assert all(action["type"] == "open_url" for action in plan)


def test_action_executor_executes_actions():
    controller = DummyController()
    executor = ActionExecutor(controller)
    result = executor.execute("open https://example.com", dry_run=False)
    assert controller.actions[0]["url"] == "https://example.com"
    assert result == [{"result": "ok"}]
