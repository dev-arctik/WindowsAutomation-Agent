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


MAX_ITERATIONS = 20


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
    status: str  # planning, finding_window, executing, verifying, complete, failed
    iteration_count: int
    next_node: str



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
        "messages": [AIMessage(
            content=f"Plan created for '{target}': {summary}\n"
            f"Steps: {len(planned)}"
        )],
    }



def action_executor(state: AutomationState) -> dict:
    """Execute the next planned action step."""
    llm = get_llm()
    llm_with_tools = llm.bind_tools(all_tools)

    current = state.get("current_step", 0)
    planned = state.get("planned_actions", [])

    if current >= len(planned):
        return {
            "messages": [AIMessage(content="All planned steps executed.")],
            "status": "verifying",
        }

    step = planned[current]
    prompt = (
        f"Execute ONLY this one step — do not call any other tools.\n"
        f"Step {step['step_number']}: {step['action']}\n"
        f"Tool: {step['tool_name']}\n"
        f"Arguments: {step['tool_args']}\n"
        f"Target app: {state['target_app']}\n\n"
        f"Call EXACTLY the tool '{step['tool_name']}' with the given arguments. "
        f"Do NOT call any other tools. Make exactly ONE tool call."
    )
    messages = [SystemMessage(content=prompt)] + list(state["messages"])
    response = llm_with_tools.invoke(messages)

    return {
        "messages": [response],
        "status": "executing",
        "current_step": current + 1,
    }


def verifier(state: AutomationState) -> dict:
    """Verify the last action succeeded using inspection tools."""
    llm = get_llm()
    llm_with_tools = llm.bind_tools(inspect_tools)

    current = state.get("current_step", 0)
    planned = state.get("planned_actions", [])
    results = state.get("execution_results", [])

    # Get the step we're verifying (the one just executed)
    step_idx = max(0, current - 1)
    if step_idx < len(planned):
        step = planned[step_idx]
        verification = step.get("verification", "Check for errors")
    else:
        verification = "Verify the overall task completed successfully"

    prompt = (
        f"Verify that the last action succeeded.\n"
        f"Verification criteria: {verification}\n"
        f"Target app: {state['target_app']}\n"
        f"Recent results: {results[-3:] if results else 'none'}\n\n"
        f"Use inspection tools to check the current state of the application. "
        f"Report whether the action succeeded or failed."
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
    summary = "; ".join(results[-5:]) if results else "Task completed"
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
    return _handle_tool_result(state)


def verifier_post(state: AutomationState) -> dict:
    return _handle_tool_result(state)


# ---------------------------------------------------------------------------
# Routing helpers for tool loops
# ---------------------------------------------------------------------------

def _route_or_return(back_to: str):
    """Create a router that goes back to the agent or to supervisor."""
    def router(state: AutomationState) -> str:
        result = tools_condition(state)
        if result == "tools":
            return f"{back_to}_tools"
        return "supervisor"
    return router


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
    builder.add_node("action_executor_tools", ToolNode(all_tools))
    builder.add_node("verifier", verifier)
    builder.add_node("verifier_tools", ToolNode(inspect_tools))
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
        _route_or_return("action_executor"),
        {
            "action_executor_tools": "action_executor_tools",
            "supervisor": "supervisor",
        },
    )
    builder.add_edge("action_executor_tools", "action_executor")

    # --- Verifier agent loop ---
    builder.add_conditional_edges(
        "verifier",
        _route_or_return("verifier"),
        {
            "verifier_tools": "verifier_tools",
            "supervisor": "supervisor",
        },
    )
    builder.add_edge("verifier_tools", "verifier")

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
