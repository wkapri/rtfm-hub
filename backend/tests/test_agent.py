import pytest
from ragapp.llm.base import AssistantTurn, ToolCall, ToolSpec

from hubapp.agent import AgentError, Tool, run_agent_loop
from hubapp.observability import Trace


class FakeLLM:
    """Returns a scripted sequence of AssistantTurns, one per complete_with_tools
    call — no network, no real model. Lets the loop's control flow (tool
    execution, message threading, termination) be tested independently of any
    provider's wire format, which test_llm_tools.py in rtfm-rag already covers.
    """

    def __init__(self, turns: list[AssistantTurn]):
        self._turns = list(turns)
        self.calls: list[list[dict]] = []

    def complete_with_tools(self, messages, tools, system_prompt):
        self.calls.append(messages)
        return self._turns.pop(0)


def _echo_tool(**kwargs) -> str:
    return f"got {kwargs}"


def test_terminal_tool_call_ends_loop_and_returns_its_arguments():
    llm = FakeLLM(
        [AssistantTurn(tool_calls=[ToolCall(id="1", name="finish", arguments={"answer": 42})])]
    )
    tools = [Tool(ToolSpec("finish", "done", {}), _echo_tool)]

    result = run_agent_loop(llm, "sys", "go", tools, terminal_tool_name="finish", trace=Trace())

    assert result == {"answer": 42}


def test_non_terminal_tool_is_executed_and_fed_back():
    llm = FakeLLM(
        [
            AssistantTurn(tool_calls=[ToolCall(id="1", name="search", arguments={"q": "roomba"})]),
            AssistantTurn(tool_calls=[ToolCall(id="2", name="finish", arguments={"answer": "done"})]),
        ]
    )
    tools = [
        Tool(ToolSpec("search", "search", {}), _echo_tool),
        Tool(ToolSpec("finish", "done", {}), _echo_tool),
    ]

    result = run_agent_loop(llm, "sys", "go", tools, terminal_tool_name="finish", trace=Trace())

    assert result == {"answer": "done"}
    # The second call's message history should include the first tool's result.
    second_call_messages = llm.calls[1]
    tool_result_messages = [m for m in second_call_messages if m["role"] == "tool"]
    assert tool_result_messages == [{"role": "tool", "tool_call_id": "1", "content": "got {'q': 'roomba'}"}]


def test_failing_tool_feeds_error_back_instead_of_raising():
    def _boom(**kwargs):
        raise ValueError("network is down")

    llm = FakeLLM(
        [
            AssistantTurn(tool_calls=[ToolCall(id="1", name="search", arguments={})]),
            AssistantTurn(tool_calls=[ToolCall(id="2", name="finish", arguments={"ok": True})]),
        ]
    )
    tools = [
        Tool(ToolSpec("search", "search", {}), _boom),
        Tool(ToolSpec("finish", "done", {}), _echo_tool),
    ]

    result = run_agent_loop(llm, "sys", "go", tools, terminal_tool_name="finish", trace=Trace())

    assert result == {"ok": True}
    tool_result = next(m for m in llm.calls[1] if m["role"] == "tool")
    assert "network is down" in tool_result["content"]


def test_text_response_gets_nudged_then_succeeds():
    # The model "summarizes" in text instead of calling the terminal tool —
    # a real small-model quirk found via live testing. The loop should nudge
    # it once rather than failing immediately.
    llm = FakeLLM(
        [
            AssistantTurn(tool_calls=[], text="Based on my search, the answer is 42."),
            AssistantTurn(tool_calls=[ToolCall(id="1", name="finish", arguments={"answer": 42})]),
        ]
    )
    tools = [Tool(ToolSpec("finish", "done", {}), _echo_tool)]

    result = run_agent_loop(llm, "sys", "go", tools, terminal_tool_name="finish", trace=Trace())

    assert result == {"answer": 42}
    nudge = next(m for m in llm.calls[1] if m["role"] == "user" and "Call finish now" in m["content"])
    assert nudge


def test_text_response_twice_in_a_row_raises_agent_error():
    llm = FakeLLM(
        [
            AssistantTurn(tool_calls=[], text="Still thinking..."),
            AssistantTurn(tool_calls=[], text="I'm not sure what to do."),
        ]
    )
    tools = [Tool(ToolSpec("finish", "done", {}), _echo_tool)]

    with pytest.raises(AgentError, match="stopped without calling"):
        run_agent_loop(llm, "sys", "go", tools, terminal_tool_name="finish", trace=Trace())


def test_exceeding_max_iterations_raises_agent_error():
    llm = FakeLLM(
        [AssistantTurn(tool_calls=[ToolCall(id=str(i), name="search", arguments={})]) for i in range(3)]
    )
    tools = [Tool(ToolSpec("search", "search", {}), _echo_tool), Tool(ToolSpec("finish", "done", {}), _echo_tool)]

    with pytest.raises(AgentError, match="didn't call 'finish'"):
        run_agent_loop(llm, "sys", "go", tools, terminal_tool_name="finish", trace=Trace(), max_iterations=3)


def test_every_step_is_traced():
    llm = FakeLLM(
        [
            AssistantTurn(tool_calls=[ToolCall(id="1", name="search", arguments={"q": "x"})]),
            AssistantTurn(tool_calls=[ToolCall(id="2", name="finish", arguments={})]),
        ]
    )
    tools = [Tool(ToolSpec("search", "search", {}), _echo_tool), Tool(ToolSpec("finish", "done", {}), _echo_tool)]
    trace = Trace()

    run_agent_loop(llm, "sys", "go", tools, terminal_tool_name="finish", trace=trace)

    step_names = [s.name for s in trace.steps]
    assert step_names == ["agent_turn", "tool:search", "agent_turn"]
