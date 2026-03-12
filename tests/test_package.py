from agentfirewall import AgentFirewall, DecisionAction, EventContext, protect


def test_protect_returns_original_agent() -> None:
    class DummyAgent:
        pass

    agent = DummyAgent()

    protected = protect(agent)

    assert protected is agent
    assert isinstance(agent.__agentfirewall__, AgentFirewall)


def test_wrap_agent_returns_original_agent() -> None:
    class DummyAgent:
        pass

    agent = DummyAgent()
    firewall = AgentFirewall()

    wrapped = firewall.wrap_agent(agent)

    assert wrapped is agent
    assert agent.__agentfirewall__ is firewall


def test_evaluate_uses_default_action_when_no_rule_matches() -> None:
    firewall = AgentFirewall()

    decision = firewall.evaluate(EventContext(kind="tool_call"))

    assert decision.action == DecisionAction.ALLOW
