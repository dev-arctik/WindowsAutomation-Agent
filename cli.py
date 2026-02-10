"""
Typer CLI entrypoint for WindowsAutomation-Agent.

Usage:
    poetry run python cli.py run "open notepad and type hello world"
    poetry run python cli.py inspect notepad
    poetry run python cli.py list-windows
"""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from langchain_core.messages import HumanMessage

app = typer.Typer(
    name="winautomation",
    help="AI-powered Windows GUI automation agent",
)
console = Console()


def _safe(text: str) -> str:
    """Strip characters that can't be encoded in the Windows console (cp1252)."""
    return text.encode("cp1252", errors="replace").decode("cp1252")


@app.command()
def run(
    command: str = typer.Argument(help="Natural language automation command"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed messages"),
) -> None:
    """Run the automation agent with a natural language command."""
    from graphs.automation_graph import build_automation_graph

    console.print(Panel(
        f"[bold cyan]{command}[/bold cyan]",
        title="Automation Command",
        border_style="blue",
    ))

    with console.status("[bold green]Building automation graph..."):
        graph = build_automation_graph()

    config = {"configurable": {"thread_id": "cli-1"}}

    console.print("\n[bold]Running automation...[/bold]\n")

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
            "retry_count": 0,
            "step_failed": False,
        },
        config,
    )

    # Status panel
    status = result.get("status", "unknown")
    status_color = "green" if status == "complete" else "red" if status == "failed" else "yellow"
    console.print(Panel(
        f"[bold {status_color}]{status.upper()}[/bold {status_color}]",
        title="Result",
        border_style=status_color,
    ))

    # Execution steps table
    planned = result.get("planned_actions", [])
    exec_results = result.get("execution_results", [])
    if planned:
        from graphs.automation_graph import _result_has_error

        table = Table(title="Execution Steps", show_lines=True)
        table.add_column("#", style="cyan", width=4)
        table.add_column("Action", style="white")
        table.add_column("Tool", style="green")
        table.add_column("Status", style="yellow")

        current = result.get("current_step", 0)
        for step in planned:
            step_num = step["step_number"]
            if step_num <= current:
                step_status = "[green]Done[/green]"
            else:
                step_status = "[yellow]Pending[/yellow]"
            table.add_row(
                str(step_num),
                step["action"],
                step["tool_name"],
                step_status,
            )
        console.print(table)

        # Show error summary if any
        error_count = sum(1 for r in exec_results if _result_has_error(r))
        if error_count > 0:
            console.print(
                f"\n[bold yellow]Warning: {error_count} tool call(s) had errors "
                f"(retried or skipped)[/bold yellow]"
            )

    # Execution results
    results = result.get("execution_results", [])
    if results:
        console.print("\n[bold]Execution Log:[/bold]")
        for i, r in enumerate(results, 1):
            console.print(f"  {i}. {_safe(r)}")

    # Verbose message output
    if verbose:
        console.print("\n[bold]Messages:[/bold]")
        for msg in result.get("messages", []):
            if hasattr(msg, "content") and msg.content:
                role = getattr(msg, "type", "unknown")
                console.print(f"  [{role}] {_safe(msg.content[:200])}")


@app.command()
def inspect(
    app_name: str = typer.Argument(help="Application name to inspect"),
) -> None:
    """Connect to an app and dump its control tree."""
    from tools.window_tools import connect_to_app
    from tools.inspect_tools import inspect_control_tree

    with console.status(f"[bold green]Connecting to {app_name}..."):
        result = connect_to_app.invoke({"app_name": app_name})
    console.print(result)

    with console.status("[bold green]Inspecting control tree..."):
        tree = inspect_control_tree.invoke({"app_name": app_name})
    console.print(Panel(tree, title=f"Control Tree: {app_name}", border_style="blue"))


@app.command(name="list-windows")
def list_windows_cmd() -> None:
    """List all visible windows on the desktop."""
    from tools.window_tools import list_windows

    with console.status("[bold green]Listing windows..."):
        result = list_windows.invoke({})
    console.print(result)


if __name__ == "__main__":
    app()
