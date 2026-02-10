"""
Main automation supervisor graph.

Orchestrates the full automation flow: intent parsing → app discovery →
action planning → execution → verification using a supervisor pattern
that routes between specialized sub-agents.
"""

import operator
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from config.config import get_llm  # used by action_executor, verifier
from graphs.planner_graph import build_planner_graph
from tools import all_tools, inspect_tools

# Build a name→function lookup for direct tool invocation
_TOOL_BY_NAME = {t.name: t for t in all_tools}


MAX_ITERATIONS = 30

# Error patterns that indicate a tool call failed
ERROR_PATTERNS = [
    "is not connected",
    "Control not found",
    "timed out",
    "Failed to find control",
    "could not get window",
    "Could not start",
    "Could not connect",
    "Click failed",
    "Type failed",
    "failed:",
    "error:",
    "Menu selection failed",
    "Selection failed",
]


def _result_has_error(text: str) -> bool:
    """Check if a tool result string contains an error pattern."""
    lower = text.lower()
    return any(p.lower() in lower for p in ERROR_PATTERNS)


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


class AutomationState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    user_command: str
    target_app: str
    planned_actions: list[dict]
    current_step: int
    execution_results: Annotated[list[str], operator.add]
    status: str  # planning, executing, verifying, complete, failed
    iteration_count: int
    next_node: str
    retry_count: int  # track retries for current step
    step_failed: bool  # flag when current step has an error


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------


def supervisor(state: AutomationState) -> dict:
    """Deterministic routing based on state — no LLM call needed.

    Decision tree:
    1. No plan yet (planned_actions empty)       → intent_parser
    2. Steps remaining (current_step < total)    → action_executor
    3. All steps done, verifier hasn't run yet   → verifier
    4. Verifier already ran (status="verifying")  → complete
    5. Max iterations exceeded                    → failed
    """
    iteration = state.get("iteration_count", 0) + 1

    if iteration > MAX_ITERATIONS:
        return {
            "next_node": "failed",
            "status": "failed",
            "iteration_count": iteration,
            "messages": [AIMessage(content="Max iterations reached. Stopping.")],
        }

    planned = state.get("planned_actions", [])
    current_step = state.get("current_step", 0)
    status = state.get("status", "starting")

    if not planned:
        next_node = "intent_parser"
    elif current_step < len(planned):
        next_node = "action_executor"
    elif status in ("verifying", "verified", "verification_failed"):
        # Verifier already ran — done
        next_node = "complete"
    else:
        # All steps executed, verifier hasn't run yet
        next_node = "verifier"

    return {
        "next_node": next_node,
        "iteration_count": iteration,
    }


def supervisor_router(state: AutomationState) -> str:
    """Route to the node decided by the supervisor."""
    return state["next_node"]


def intent_parser(state: AutomationState) -> dict:
    """Invoke the planner sub-graph to create an action plan."""
    planner = build_planner_graph()

    plan_result = planner.invoke({
        "messages": [HumanMessage(content=state["user_command"])],
        "user_command": state["user_command"],
        "target_app": "",
        "planned_actions": [],
        "plan_summary": "",
    })

    planned = plan_result.get("planned_actions", [])
    target = plan_result.get("target_app", "")
    summary = plan_result.get("plan_summary", "")

    return {
        "target_app": target,
        "planned_actions": planned,
        "status": "planned",
        "current_step": 0,
        "retry_count": 0,
        "step_failed": False,
        "messages": [AIMessage(
            content=f"Plan created for '{target}': {summary}\n"
            f"Steps: {len(planned)}"
        )],
    }


def _can_direct_invoke(step: dict, retry_count: int) -> bool:
    """Check if a step can be directly invoked without LLM mediation.

    Direct invocation is used when:
    1. This is NOT a retry (retries need LLM creativity)
    2. The tool_name maps to a known tool
    3. The tool_args are complete (non-empty)
    """
    if retry_count > 0:
        return False
    tool_name = step.get("tool_name", "")
    tool_args = step.get("tool_args", {})
    if tool_name not in _TOOL_BY_NAME:
        return False
    if not tool_args:
        return False
    return True


def action_executor(state: AutomationState) -> dict:
    """Execute the next planned action step.

    Uses a two-tier strategy:
    1. DIRECT INVOCATION: For steps with exact tool_name + tool_args from the
       planner (e.g., Calculator button clicks). Bypasses LLM entirely for
       deterministic, order-preserving execution.
    2. LLM-MEDIATED: For retries, incomplete args, or unknown tools. The LLM
       picks the right tool call with full context and error recovery hints.
    """
    current = state.get("current_step", 0)
    planned = state.get("planned_actions", [])
    retry_count = state.get("retry_count", 0)
    results = state.get("execution_results", [])

    if current >= len(planned):
        return {
            "messages": [AIMessage(content="All planned steps executed.")],
            "status": "all_steps_done",
        }

    step = planned[current]

    # --- Tier 1: Direct invocation (deterministic, no LLM) ---
    if _can_direct_invoke(step, retry_count):
        tool_name = step["tool_name"]
        tool_args = step["tool_args"]
        tool_fn = _TOOL_BY_NAME[tool_name]
        try:
            result_str = tool_fn.invoke(tool_args)
        except Exception as e:
            result_str = f"Tool error: {e}"

        # Store result and signal step_result_checker directly
        return {
            "messages": [AIMessage(
                content=f"[Direct] Step {step['step_number']}: {step['action']} -> {result_str}"
            )],
            "execution_results": [str(result_str)[:500]],
            "status": "executing_direct",
        }

    # --- Tier 2: LLM-mediated invocation (for retries / complex steps) ---
    llm = get_llm()
    llm_with_tools = llm.bind_tools(all_tools)

    # Build context about what happened so far
    recent_results = results[-5:] if results else []
    results_context = ""
    if recent_results:
        results_context = (
            "\n\nPrevious execution results (for context):\n"
            + "\n".join(f"  - {r}" for r in recent_results)
        )

    # If retrying, add error recovery guidance
    retry_context = ""
    if retry_count > 0:
        retry_context = (
            f"\n\nThis is retry #{retry_count} for this step. "
            f"The previous attempt FAILED. You MUST try a DIFFERENT approach:\n"
            f"  - If a control was not found by title, try using auto_id instead\n"
            f"  - If the app was 'not connected', call connect_to_app first\n"
            f"  - If a click failed, try inspect_control_tree to find the right control\n"
            f"  - You may call multiple tools if needed to accomplish this step"
        )

    prompt = (
        f"Execute this automation step:\n"
        f"Step {step['step_number']}: {step['action']}\n"
        f"Suggested tool: {step['tool_name']}\n"
        f"Suggested arguments: {step['tool_args']}\n"
        f"Target app: {state['target_app']}\n"
        f"{retry_context}"
        f"{results_context}\n\n"
        f"Call the appropriate tool(s) to accomplish this step. "
        f"Use EXACTLY the suggested tool and arguments unless they clearly "
        f"won't work. You can call connect_to_app if the app is "
        f"not connected, or inspect_control_tree to discover controls."
    )
    messages = [SystemMessage(content=prompt)] + list(state["messages"])
    response = llm_with_tools.invoke(messages)

    # DON'T advance current_step here — wait until we verify the tool result
    return {
        "messages": [response],
        "status": "executing",
    }


def step_result_checker(state: AutomationState) -> dict:
    """Check if the last tool execution succeeded or failed.

    Examines the most recent tool message for error patterns.
    If failed, either retry (up to 2 times) or skip and continue.
    """
    results = state.get("execution_results", [])
    current = state.get("current_step", 0)
    retry_count = state.get("retry_count", 0)

    # Get the last result
    last_result = results[-1] if results else ""

    if _result_has_error(last_result):
        # Step failed
        if retry_count < 2:
            # Retry this step
            return {
                "retry_count": retry_count + 1,
                "step_failed": True,
                "messages": [AIMessage(
                    content=f"Step {current + 1} failed: {last_result[:200]}. Retrying..."
                )],
            }
        else:
            # Max retries exhausted — skip this step and continue
            return {
                "current_step": current + 1,
                "retry_count": 0,
                "step_failed": False,
                "messages": [AIMessage(
                    content=f"Step {current + 1} failed after {retry_count + 1} attempts. Skipping."
                )],
            }
    else:
        # Step succeeded — advance
        return {
            "current_step": current + 1,
            "retry_count": 0,
            "step_failed": False,
        }


def step_result_router(state: AutomationState) -> str:
    """Route based on step result: retry or go back to supervisor."""
    if state.get("step_failed", False):
        return "action_executor"  # retry
    return "supervisor"  # success or max retries exhausted


def verifier(state: AutomationState) -> dict:
    """Verify the overall task succeeded using inspection tools.

    Checks execution_results for error patterns and uses inspect tools
    to verify the final state of the application.
    """
    llm = get_llm()
    llm_with_tools = llm.bind_tools(inspect_tools)

    results = state.get("execution_results", [])
    planned = state.get("planned_actions", [])

    # Count how many steps had errors
    error_count = sum(1 for r in results if _result_has_error(r))
    total_steps = len(planned)
    success_results = [r for r in results if not _result_has_error(r)]

    prompt = (
        f"Verify that the automation task completed successfully.\n"
        f"Original command: {state['user_command']}\n"
        f"Target app: {state['target_app']}\n"
        f"Total planned steps: {total_steps}\n"
        f"Steps with errors: {error_count}\n\n"
        f"Recent execution results:\n"
        + "\n".join(f"  - {r}" for r in results[-8:])
        + f"\n\nUse inspect_control_tree or get_control_properties to check "
        f"the current state of '{state['target_app']}'. "
        f"Report whether the task succeeded or failed, and what the current "
        f"state of the app is."
    )
    messages = [SystemMessage(content=prompt)] + list(state["messages"])
    response = llm_with_tools.invoke(messages)

    return {
        "messages": [response],
        "status": "verifying",
    }


def complete(state: AutomationState) -> dict:
    """Terminal node for successful completion."""
    results = state.get("execution_results", [])
    error_count = sum(1 for r in results if _result_has_error(r))
    success_results = [r for r in results if not _result_has_error(r)]

    if error_count > 0:
        summary = (
            f"Completed with {error_count} error(s). "
            f"Successes: {'; '.join(success_results[-3:]) if success_results else 'none'}"
        )
    else:
        summary = "; ".join(success_results[-5:]) if success_results else "Task completed"

    return {
        "status": "complete",
        "messages": [AIMessage(content=f"Automation complete. {summary}")],
    }


def failed(state: AutomationState) -> dict:
    """Terminal node for failure."""
    results = state.get("execution_results", [])
    summary = "; ".join(results[-3:]) if results else "Unknown error"
    return {
        "status": "failed",
        "messages": [AIMessage(content=f"Automation failed. {summary}")],
    }


# ---------------------------------------------------------------------------
# Tool result handlers
# ---------------------------------------------------------------------------

def _handle_tool_result(state: AutomationState) -> dict:
    """Capture tool results into execution_results."""
    last = state["messages"][-1] if state["messages"] else None
    if last and hasattr(last, "content"):
        return {"execution_results": [str(last.content)[:500]]}
    return {}


def executor_post(state: AutomationState) -> dict:
    """Capture tool results into execution_results after action_executor tools run."""
    return _handle_tool_result(state)


def verifier_post(state: AutomationState) -> dict:
    """Capture tool results into execution_results after verifier tools run."""
    return _handle_tool_result(state)


# ---------------------------------------------------------------------------
# Custom ToolNode with error capturing
# ---------------------------------------------------------------------------

def _tool_error_handler(error: Exception) -> str:
    """Return a readable error message instead of crashing."""
    return f"Tool error: {str(error)}"


# ---------------------------------------------------------------------------
# Routing helpers for tool loops
# ---------------------------------------------------------------------------

def _route_executor(state: AutomationState) -> str:
    """Route from action_executor: direct results go to checker, LLM tool calls go to ToolNode."""
    # Direct invocations already have their result — go straight to checker
    if state.get("status") == "executing_direct":
        return "step_result_checker"
    # LLM-mediated: check if the LLM wants to call tools
    result = tools_condition(state)
    if result == "tools":
        return "action_executor_tools"
    return "step_result_checker"


def _route_verifier(state: AutomationState) -> str:
    """Route from verifier: to tools if tool call, else to supervisor."""
    result = tools_condition(state)
    if result == "tools":
        return "verifier_tools"
    return "supervisor"


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------


def build_automation_graph():
    """Build and compile the main automation supervisor graph."""
    builder = StateGraph(AutomationState)

    # --- Nodes ---
    builder.add_node("supervisor", supervisor)
    builder.add_node("intent_parser", intent_parser)
    builder.add_node("action_executor", action_executor)
    builder.add_node("action_executor_tools", ToolNode(
        all_tools,
        handle_tool_errors=_tool_error_handler,
    ))
    builder.add_node("executor_post", executor_post)
    builder.add_node("step_result_checker", step_result_checker)
    builder.add_node("verifier", verifier)
    builder.add_node("verifier_tools", ToolNode(
        inspect_tools,
        handle_tool_errors=_tool_error_handler,
    ))
    builder.add_node("verifier_post", verifier_post)
    builder.add_node("complete", complete)
    builder.add_node("failed", failed)

    # --- Entry ---
    builder.add_edge(START, "supervisor")

    # --- Supervisor routing ---
    builder.add_conditional_edges(
        "supervisor",
        supervisor_router,
        {
            "intent_parser": "intent_parser",
            "action_executor": "action_executor",
            "verifier": "verifier",
            "complete": "complete",
            "failed": "failed",
        },
    )

    # --- Intent parser → supervisor ---
    builder.add_edge("intent_parser", "supervisor")

    # --- Action executor agent loop ---
    builder.add_conditional_edges(
        "action_executor",
        _route_executor,
        {
            "action_executor_tools": "action_executor_tools",
            "step_result_checker": "step_result_checker",
        },
    )
    # After tools execute, capture results then come back to action_executor
    builder.add_edge("action_executor_tools", "executor_post")
    builder.add_edge("executor_post", "action_executor")

    # --- Step result checker: retry or continue ---
    builder.add_conditional_edges(
        "step_result_checker",
        step_result_router,
        {
            "action_executor": "action_executor",
            "supervisor": "supervisor",
        },
    )

    # --- Verifier agent loop ---
    builder.add_conditional_edges(
        "verifier",
        _route_verifier,
        {
            "verifier_tools": "verifier_tools",
            "supervisor": "supervisor",
        },
    )
    builder.add_edge("verifier_tools", "verifier_post")
    builder.add_edge("verifier_post", "verifier")

    # --- Terminal nodes ---
    builder.add_edge("complete", END)
    builder.add_edge("failed", END)

    # --- Compile ---
    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)


# ---------------------------------------------------------------------------
# Interactive test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    graph = build_automation_graph()
    config = {"configurable": {"thread_id": "1"}}

    print("WindowsAutomation Agent (type 'quit' to exit)")
    print("-" * 50)

    while True:
        user_input = input("\nYou: ").strip()
        if user_input.lower() in ("quit", "exit", "q"):
            break

        result = graph.invoke(
            {
                "messages": [HumanMessage(content=user_input)],
                "user_command": user_input,
                "target_app": "",
                "planned_actions": [],
                "current_step": 0,
                "execution_results": [],
                "status": "starting",
                "iteration_count": 0,
                "next_node": "",
                "retry_count": 0,
                "step_failed": False,
            },
            config,
        )

        print(f"\nStatus: {result['status']}")
        print(f"Target app: {result.get('target_app', 'N/A')}")
        print(f"Steps completed: {result.get('current_step', 0)}/{len(result.get('planned_actions', []))}")

        # Print final messages
        for msg in result["messages"][-3:]:
            if hasattr(msg, "content") and msg.content:
                role = getattr(msg, "type", "unknown")
                print(f"\n[{role}] {msg.content}")
