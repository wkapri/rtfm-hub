from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ragapp.llm.base import LLMProvider, Message, ToolCall, ToolSpec

from hubapp.observability import Trace


class AgentError(Exception):
    """The agent loop didn't reach a terminal answer — it ran out of
    iterations, or the model stopped without calling the terminal tool."""


@dataclass
class Tool:
    spec: ToolSpec
    impl: Callable[..., Any]  # takes the model's **arguments, returns a stringifiable result


def run_agent_loop(
    llm: LLMProvider,
    system_prompt: str,
    user_message: str,
    tools: list[Tool],
    terminal_tool_name: str,
    trace: Trace,
    max_iterations: int = 6,
) -> dict[str, Any]:
    """Run a ReAct-style tool-calling loop: the model can call any of `tools`
    as many times as it wants (searching again with a different query, fetching
    a page to confirm a detail, etc.), and the loop ends only when it calls the
    designated terminal tool — that call's arguments ARE the loop's result.
    Ending on a dedicated tool call (rather than parsing free text once the
    model "seems done") is what makes the result structured without needing
    the regex JSON-extraction this replaced.

    Every model turn and every tool call becomes a trace step, so the full
    reasoning trail is visible in the "What happened" panel, not just the
    final answer — this is exactly the kind of multi-step, otherwise-opaque
    process that mechanism was built for.

    A tool implementation that raises is not fatal to the loop: the error is
    fed back to the model as that tool's result (a broken search or fetch is
    something the model can react to — try a different query, a different
    URL — not something that should crash the whole request).

    A smaller model (this project's default is a local 3B one) will sometimes
    gather what it needs via tools and then summarize in plain text instead of
    actually calling the terminal tool — it "sounds" done without formally
    finishing. Found via live testing: llama3.2:3b did this consistently after
    one search, even with a good candidate in hand. Rather than fail the whole
    request on the first occurrence, the loop nudges once — tells the model
    plainly that it must call the terminal tool now — before giving up.
    """
    tool_map = {t.spec.name: t for t in tools}
    tool_specs = [t.spec for t in tools]
    messages: list[Message] = [{"role": "user", "content": user_message}]
    nudged = False

    for _ in range(max_iterations):
        with trace.step("agent_turn") as s:
            turn = llm.complete_with_tools(messages, tool_specs, system_prompt)
            s.detail = (
                f"called {', '.join(tc.name for tc in turn.tool_calls)}"
                if turn.tool_calls
                else "text response (no tool call)"
            )

        if not turn.tool_calls:
            if nudged:
                raise AgentError(
                    f"Model stopped without calling {terminal_tool_name!r}: {(turn.text or '')[:200]!r}"
                )
            messages.append({"role": "assistant", "content": turn.text, "tool_calls": []})
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"Call {terminal_tool_name} now to finish, using your best judgment from "
                        "what you've found so far."
                    ),
                }
            )
            nudged = True
            continue

        messages.append({"role": "assistant", "content": turn.text, "tool_calls": turn.tool_calls})

        terminal_call = next((tc for tc in turn.tool_calls if tc.name == terminal_tool_name), None)
        if terminal_call is not None:
            return terminal_call.arguments

        for call in turn.tool_calls:
            messages.append({"role": "tool", "tool_call_id": call.id, "content": _run_tool(call, tool_map, trace)})

    raise AgentError(f"Agent didn't call {terminal_tool_name!r} within {max_iterations} turn(s).")


def _run_tool(call: ToolCall, tool_map: dict[str, Tool], trace: Trace) -> str:
    with trace.step(f"tool:{call.name}") as s:
        tool = tool_map.get(call.name)
        if tool is None:
            result = f"Error: unknown tool {call.name!r}"
        else:
            try:
                result = str(tool.impl(**call.arguments))
            except Exception as exc:  # noqa: BLE001 — handed back to the model as a recoverable tool error
                result = f"Error: {exc}"
        s.detail = result[:200]
    return result
