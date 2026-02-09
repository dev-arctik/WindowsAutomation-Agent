"""
Experiment 001: Basic Notepad automation.

Tests the full automation pipeline: open Notepad, type text, save file.
Also supports --direct mode for testing tools without the graph.
"""

import argparse

from langchain_core.messages import HumanMessage
from rich.console import Console
from rich.panel import Panel

console = Console()

COMMAND = "Open Notepad, type 'Hello World from WindowsAutomation Agent!', then save the file as test_output.txt"


def run_with_graph(command: str) -> None:
    """Run the automation using the full LangGraph supervisor."""
    from graphs.automation_graph import build_automation_graph

    console.print(Panel(
        f"[bold cyan]{command}[/bold cyan]",
        title="Graph Mode",
        border_style="blue",
    ))

    graph = build_automation_graph()
    config = {"configurable": {"thread_id": "experiment-001"}}

    result = graph.invoke(
        {
            "messages": [HumanMessage(content=command)],
            "user_command": command,
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

    console.print(f"\n[bold]Status:[/bold] {result['status']}")
    console.print(f"[bold]Target app:[/bold] {result.get('target_app', 'N/A')}")
    console.print(f"[bold]Steps:[/bold] {result.get('current_step', 0)}/{len(result.get('planned_actions', []))}")

    for msg in result["messages"][-3:]:
        if hasattr(msg, "content") and msg.content:
            console.print(f"\n[dim]{msg.content}[/dim]")


def run_direct() -> None:
    """Run tools directly without the graph (for testing)."""
    from tools.window_tools import connect_to_app, list_windows
    from tools.input_tools import type_text, press_keys
    from tools.inspect_tools import inspect_control_tree

    console.print(Panel(
        "[bold yellow]Direct Tool Testing Mode[/bold yellow]",
        title="Direct Mode",
        border_style="yellow",
    ))

    # Step 1: List windows
    console.print("\n[bold]Step 1: Listing windows[/bold]")
    result = list_windows.invoke({})
    console.print(result)

    # Step 2: Connect to notepad
    console.print("\n[bold]Step 2: Connecting to Notepad[/bold]")
    result = connect_to_app.invoke({"app_name": "notepad", "start_if_not_found": True})
    console.print(result)

    # Step 3: Inspect control tree
    console.print("\n[bold]Step 3: Inspecting control tree[/bold]")
    result = inspect_control_tree.invoke({"app_name": "notepad"})
    console.print(result)

    # Step 4: Type text
    console.print("\n[bold]Step 4: Typing text[/bold]")
    result = type_text.invoke({"app_name": "notepad", "text": "Hello World from WindowsAutomation Agent!"})
    console.print(result)

    # Step 5: Press Ctrl+S
    console.print("\n[bold]Step 5: Pressing Ctrl+S[/bold]")
    result = press_keys.invoke({"app_name": "notepad", "keys": "^s"})
    console.print(result)

    console.print("\n[bold green]Direct test complete![/bold green]")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Experiment 001: Basic Notepad automation")
    parser.add_argument(
        "--direct",
        action="store_true",
        help="Run tools directly without the graph",
    )
    parser.add_argument(
        "--command",
        type=str,
        default=COMMAND,
        help="Custom command to run in graph mode",
    )
    args = parser.parse_args()

    if args.direct:
        run_direct()
    else:
        run_with_graph(args.command)
