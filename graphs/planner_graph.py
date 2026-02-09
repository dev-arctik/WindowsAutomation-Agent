"""
Task planning sub-graph.

Takes a user command and produces a structured action plan
with target app, ordered steps, and tool calls.
"""

from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from config.config import get_llm


# ---------------------------------------------------------------------------
# Pydantic models for structured output
# ---------------------------------------------------------------------------


class ActionStep(BaseModel):
    """A single step in the automation plan."""

    step_number: int = Field(description="Sequential step number starting from 1")
    action: str = Field(description="Human-readable description of what this step does")
    tool_name: str = Field(description="Name of the tool to call for this step")
    tool_args: dict = Field(
        description="Arguments to pass to the tool",
        default_factory=dict,
    )
    verification: str = Field(
        description="How to verify this step succeeded",
        default="Check that no error was returned",
    )


class ActionPlan(BaseModel):
    """Complete automation plan for a user command."""

    target_app: str = Field(description="The application to automate (e.g. 'notepad', 'calc')")
    steps: list[ActionStep] = Field(description="Ordered list of automation steps")
    summary: str = Field(description="Brief summary of the entire plan")


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


class PlannerState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    user_command: str
    target_app: str
    planned_actions: list[dict]
    plan_summary: str


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

PLANNER_SYSTEM_PROMPT = """You are an automation planner. Given a user's natural language command,
create a structured plan to automate it on a Windows desktop application.

Available tools you can plan for:
- connect_to_app(app_name, start_if_not_found): Connect to or start an application
- list_windows(): List all visible desktop windows
- find_window(title): Find a window by partial title match
- get_window_info(app_name): Get window details
- inspect_control_tree(app_name, depth): Inspect GUI control hierarchy
- get_control_properties(app_name, control_type, title, auto_id): Get control details
- list_child_controls(app_name, control_type): List actionable controls
- take_screenshot(app_name, filename): Screenshot the app window
- click_element(app_name, control_type, title, auto_id): Click a UI element
- type_text(app_name, text, control_type, title, auto_id, use_set_text): Type text
- press_keys(app_name, keys): Press keyboard keys (pywinauto syntax)
- select_item(app_name, item_text, control_type, title, auto_id): Select list/combo item
- menu_select(app_name, menu_path): Select a menu item (e.g. 'File->Save')

Key syntax for press_keys:
- '^s' = Ctrl+S, '%{F4}' = Alt+F4, '{ENTER}' = Enter, '{TAB}' = Tab

Rules:
1. Always start with connect_to_app to ensure the application is running
2. Use inspect_control_tree if you need to discover available controls
3. Prefer automation_id over title for control identification when possible
4. Include verification steps after critical actions
5. Keep the plan minimal — only the steps needed to accomplish the task
"""


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------


def parse_command(state: PlannerState) -> dict:
    """Parse the user command into a structured action plan."""
    llm = get_llm()
    structured_llm = llm.with_structured_output(ActionPlan)

    messages = [
        SystemMessage(content=PLANNER_SYSTEM_PROMPT),
        *state["messages"],
    ]

    plan: ActionPlan = structured_llm.invoke(messages)

    return {
        "target_app": plan.target_app,
        "planned_actions": [step.model_dump() for step in plan.steps],
        "plan_summary": plan.summary,
    }


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------


def build_planner_graph() -> StateGraph:
    """Build and compile the planner sub-graph."""
    builder = StateGraph(PlannerState)
    builder.add_node("parse_command", parse_command)
    builder.add_edge(START, "parse_command")
    builder.add_edge("parse_command", END)
    return builder.compile()


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from langchain_core.messages import HumanMessage

    graph = build_planner_graph()
    command = "Open Notepad and type Hello World"
    print(f"Planning: '{command}'\n")

    result = graph.invoke({
        "messages": [HumanMessage(content=command)],
        "user_command": command,
        "target_app": "",
        "planned_actions": [],
        "plan_summary": "",
    })

    print(f"Target app: {result['target_app']}")
    print(f"Summary: {result['plan_summary']}")
    print(f"\nSteps:")
    for step in result["planned_actions"]:
        print(f"  {step['step_number']}. {step['action']}")
        print(f"     Tool: {step['tool_name']}({step['tool_args']})")
        print(f"     Verify: {step['verification']}")
