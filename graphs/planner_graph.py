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

PLANNER_SYSTEM_PROMPT = """You are an automation planner for Windows desktop apps. Given a user's natural
language command (which may be vague or informal), create a structured plan to automate it.

Available tools you can plan for:
- start_app(app_name): Start a NEW instance of an application (always launches fresh)
- connect_to_app(app_name, start_if_not_found): Connect to a RUNNING app (or start if not found)
- list_windows(): List all visible desktop windows
- find_window(title): Find a window by partial title match
- get_window_info(app_name): Get window details
- inspect_control_tree(app_name, depth): Inspect GUI control hierarchy — USE THIS before clicking unknown controls
- get_control_properties(app_name, control_type, title, auto_id): Get control details
- list_child_controls(app_name, control_type): List actionable controls
- take_screenshot(app_name, filename): Screenshot the app window
- click_element(app_name, control_type, title, auto_id): Click a UI element
- type_text(app_name, text, control_type, title, auto_id, use_set_text): Type text into a control or window
- press_keys(app_name, keys): Press keyboard keys (pywinauto syntax)
- select_item(app_name, item_text, control_type, title, auto_id): Select list/combo item
- menu_select(app_name, menu_path): Select a menu item (e.g. 'File->Save')

Key syntax for press_keys:
- '^s' = Ctrl+S, '^n' = Ctrl+N, '%{F4}' = Alt+F4, '{ENTER}' = Enter, '{TAB}' = Tab

CRITICAL RULES:
1. When the user says "open" an app, use start_app to launch a FRESH instance.
   - For Notepad: ALWAYS add a press_keys step with '^n' (Ctrl+N) right after start_app
     to open a blank new tab (Win11 Notepad restores previous session tabs).
2. When the user says "in <app>" or wants to work with an already-running app, use connect_to_app.
3. The app_name used in ALL tool_args must be consistent. If you start_app("notepad"),
   then ALL subsequent steps must use app_name="notepad" (not "Notepad" or "NOTEPAD").
   Use lowercase app names always: "notepad", "calculator", "chrome", "paint", etc.
4. For apps where you DON'T know the control names, add an inspect_control_tree step
   BEFORE trying to click anything. The executor will read the tree and adapt.
5. For type_text into Notepad: don't specify control_type/title/auto_id — just type
   into the window directly (it focuses the text editor automatically).
6. Keep the plan minimal but CORRECT — wrong button names cause failures.
7. *** MANDATORY: tool_args MUST include ALL required parameters for the tool. ***
   - press_keys REQUIRES both "app_name" AND "keys" in tool_args
   - type_text REQUIRES both "app_name" AND "text" in tool_args
   - click_element REQUIRES "app_name" AND at least one of "control_type", "title", or "auto_id"
   - start_app REQUIRES "app_name"
   - NEVER leave out required arguments. The step will FAIL if arguments are missing.

=== NOTEPAD EXAMPLE — "open notepad and type hello, then select all and delete" ===
  step 1: start_app -> tool_args: {"app_name": "notepad"}
  step 2: press_keys -> tool_args: {"app_name": "notepad", "keys": "^n"}
  step 3: type_text -> tool_args: {"app_name": "notepad", "text": "hello"}
  step 4: press_keys -> tool_args: {"app_name": "notepad", "keys": "^a"}
  step 5: press_keys -> tool_args: {"app_name": "notepad", "keys": "{DEL}"}
=== END NOTEPAD EXAMPLE ===

=== CALCULATOR APP: MANDATORY AUTO_ID RULES ===
For Calculator: you MUST use auto_id in tool_args. NEVER use title.
Clicking by title WILL FAIL because Calculator buttons have no standard title text.

For click_element tool_args, set ONLY app_name and auto_id. Do NOT set title or control_type.

Digit auto_ids: num0Button, num1Button, num2Button, num3Button, num4Button,
  num5Button, num6Button, num7Button, num8Button, num9Button
Operator auto_ids: plusButton, minusButton, multiplyButton, divideButton, equalButton
Other auto_ids: clearButton, clearEntryButton, decimalSeparatorButton,
  percentButton, backSpaceButton, negateButton

CALCULATOR EXAMPLE — "7 * 8":
  step 1: start_app → tool_args: {"app_name": "calculator"}
  step 2: click_element → tool_args: {"app_name": "calculator", "auto_id": "clearButton"}
  step 3: click_element → tool_args: {"app_name": "calculator", "auto_id": "num7Button"}
  step 4: click_element → tool_args: {"app_name": "calculator", "auto_id": "multiplyButton"}
  step 5: click_element → tool_args: {"app_name": "calculator", "auto_id": "num8Button"}
  step 6: click_element → tool_args: {"app_name": "calculator", "auto_id": "equalButton"}

MULTI-DIGIT EXAMPLE — "25 + 17":
  step 1: start_app → tool_args: {"app_name": "calculator"}
  step 2: click_element → tool_args: {"app_name": "calculator", "auto_id": "clearButton"}
  step 3: click_element → tool_args: {"app_name": "calculator", "auto_id": "num2Button"}
  step 4: click_element → tool_args: {"app_name": "calculator", "auto_id": "num5Button"}
  step 5: click_element → tool_args: {"app_name": "calculator", "auto_id": "plusButton"}
  step 6: click_element → tool_args: {"app_name": "calculator", "auto_id": "num1Button"}
  step 7: click_element → tool_args: {"app_name": "calculator", "auto_id": "num7Button"}
  step 8: click_element → tool_args: {"app_name": "calculator", "auto_id": "equalButton"}

IMPORTANT: For multi-digit numbers, click EACH digit separately in order (2 then 5 for "25").
Always add a clearButton click right after start_app to reset the display.

=== END CALCULATOR RULES ===

HANDLING VAGUE COMMANDS:
- "open notepad and write something" → open notepad, Ctrl+N for new tab, type a reasonable sample text
- "use calculator to add 5 and 3" → start_app calculator, click clearButton, click num5Button, click plusButton, click num3Button, click equalButton
- "save the file" → press_keys with '^s'
- "close the app" → press_keys with '%{F4}'
"""


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------


def _fixup_calculator_steps(steps: list[dict], target_app: str) -> list[dict]:
    """Post-process Calculator plans to enforce auto_id usage.

    GPT-4.1-mini sometimes ignores the prompt and uses title instead of auto_id
    for Calculator buttons. This deterministic fixup catches and corrects those cases.
    """
    if target_app.lower() not in ("calculator", "calc"):
        return steps

    # Mapping from digit/operator strings to auto_ids
    digit_map = {str(i): f"num{i}Button" for i in range(10)}
    word_map = {
        "zero": "num0Button", "one": "num1Button", "two": "num2Button",
        "three": "num3Button", "four": "num4Button", "five": "num5Button",
        "six": "num6Button", "seven": "num7Button", "eight": "num8Button",
        "nine": "num9Button",
        "plus": "plusButton", "add": "plusButton", "+": "plusButton",
        "minus": "minusButton", "subtract": "minusButton", "-": "minusButton",
        "multiply": "multiplyButton", "times": "multiplyButton", "*": "multiplyButton",
        "x": "multiplyButton",
        "divide": "divideButton", "/": "divideButton",
        "equals": "equalButton", "equal": "equalButton", "=": "equalButton",
        "clear": "clearButton", "c": "clearButton",
    }
    all_map = {**digit_map, **word_map}

    for step in steps:
        if step.get("tool_name") != "click_element":
            continue
        args = step.get("tool_args", {})
        # Already has auto_id — good
        if args.get("auto_id"):
            continue
        # Try to fix from title
        title = args.get("title", "")
        if title:
            key = title.lower().strip()
            if key in all_map:
                args["auto_id"] = all_map[key]
                args.pop("title", None)
                args.pop("control_type", None)
        # Try to infer from action description
        if not args.get("auto_id"):
            action_lower = step.get("action", "").lower()
            for key, auto_id in all_map.items():
                if f"digit {key}" in action_lower or f"number {key}" in action_lower:
                    args["auto_id"] = auto_id
                    args.pop("title", None)
                    args.pop("control_type", None)
                    break
            else:
                # Check for operator keywords
                for op_word in ("plus", "add", "minus", "subtract", "multiply",
                                "times", "divide", "equal"):
                    if op_word in action_lower:
                        args["auto_id"] = all_map[op_word]
                        args.pop("title", None)
                        args.pop("control_type", None)
                        break
        step["tool_args"] = args
    return steps


def _fixup_missing_args(steps: list[dict], user_command: str) -> list[dict]:
    """Infer missing required tool_args from the action description.

    GPT-4.1-mini often generates press_keys/type_text steps without the
    actual 'keys' or 'text' values. This fixup extracts them from the
    action description or maps common patterns.
    """
    import re

    # Common keyboard shortcut patterns
    _KEY_PATTERNS: dict[str, str] = {
        "ctrl+n": "^n", "ctrl+s": "^s", "ctrl+a": "^a", "ctrl+c": "^c",
        "ctrl+v": "^v", "ctrl+x": "^x", "ctrl+z": "^z", "ctrl+f": "^f",
        "ctrl+h": "^h", "ctrl+p": "^p", "ctrl+o": "^o", "ctrl+w": "^w",
        "alt+f4": "%{F4}", "enter": "{ENTER}", "tab": "{TAB}",
        "delete": "{DEL}", "backspace": "{BACKSPACE}", "escape": "{ESC}",
        "esc": "{ESC}", "home": "{HOME}", "end": "{END}",
    }

    for step in steps:
        tool_name = step.get("tool_name", "")
        args = step.get("tool_args", {})
        action = step.get("action", "")
        action_lower = action.lower()

        # Fix press_keys missing 'keys'
        if tool_name == "press_keys" and "keys" not in args:
            inferred_keys = None

            # Try to match Ctrl+X, Alt+X patterns in action text
            ctrl_match = re.search(r"ctrl\+(\w)", action_lower)
            if ctrl_match:
                inferred_keys = f"^{ctrl_match.group(1)}"

            alt_match = re.search(r"alt\+(\w+)", action_lower)
            if alt_match and not inferred_keys:
                key = alt_match.group(1).upper()
                inferred_keys = f"%{{{key}}}"

            # Try common keyword matches
            if not inferred_keys:
                for keyword, pywinauto_key in _KEY_PATTERNS.items():
                    if keyword in action_lower:
                        inferred_keys = pywinauto_key
                        break

            # Try quoted key syntax in the action
            quoted = re.search(r"['\"]([^^%{].*?)['\"]", action)
            if quoted and not inferred_keys:
                inferred_keys = quoted.group(1)

            if inferred_keys:
                args["keys"] = inferred_keys
                step["tool_args"] = args

        # Fix type_text missing 'text'
        if tool_name == "type_text" and "text" not in args:
            inferred_text = None

            # Extract text from single or double quotes in action
            quoted = re.search(r"['\"](.+?)['\"]", action)
            if quoted:
                inferred_text = quoted.group(1)

            # Try to extract from user command if action doesn't have it
            if not inferred_text:
                cmd_quoted = re.search(r"type\s+['\"](.+?)['\"]", user_command, re.IGNORECASE)
                if cmd_quoted:
                    inferred_text = cmd_quoted.group(1)

            if inferred_text:
                args["text"] = inferred_text
                step["tool_args"] = args

    return steps


def parse_command(state: PlannerState) -> dict:
    """Parse the user command into a structured action plan."""
    llm = get_llm()
    structured_llm = llm.with_structured_output(ActionPlan, method="function_calling")

    messages = [
        SystemMessage(content=PLANNER_SYSTEM_PROMPT),
        *state["messages"],
    ]

    plan: ActionPlan = structured_llm.invoke(messages)
    steps = [step.model_dump() for step in plan.steps]

    # Post-process: ensure app_name is set in tool_args for tools that need it
    _TOOLS_NEEDING_APP_NAME = {
        "start_app", "connect_to_app", "click_element", "type_text",
        "press_keys", "select_item", "menu_select", "inspect_control_tree",
        "get_control_properties", "list_child_controls", "take_screenshot",
        "get_window_info",
    }
    for step in steps:
        tool_name = step.get("tool_name", "")
        args = step.get("tool_args", {})
        if tool_name in _TOOLS_NEEDING_APP_NAME and "app_name" not in args:
            args["app_name"] = plan.target_app.lower()
            step["tool_args"] = args

    # Post-process: fix missing keys/text args
    steps = _fixup_missing_args(steps, state["user_command"])

    # Post-process: fix Calculator steps to use auto_id
    steps = _fixup_calculator_steps(steps, plan.target_app)

    return {
        "target_app": plan.target_app,
        "planned_actions": steps,
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
