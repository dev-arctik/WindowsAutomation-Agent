"""
Window management tools for the automation agent.

Tools for listing, finding, and connecting to Windows applications.
All functions return strings so the LLM can interpret the results.
"""

import time
from typing import Any

from langchain_core.tools import tool

from utils.gui_helpers import (
    connect_to_application,
    get_window,
    list_all_windows,
    start_application,
)

# Shared registry to store connected app instances across tool calls
_app_registry: dict[str, dict[str, Any]] = {}


def get_app_registry() -> dict[str, dict[str, Any]]:
    """Get the shared app registry for cross-module access."""
    return _app_registry


@tool
def list_windows() -> str:
    """List all visible windows on the desktop.

    Returns a formatted string with window title, process ID, and class name
    for each visible top-level window.
    """
    windows = list_all_windows()
    if not windows:
        return "No visible windows found."

    lines = ["Visible windows:"]
    for i, w in enumerate(windows, 1):
        lines.append(
            f"  {i}. '{w['title']}' (PID: {w['process_id']}, "
            f"Class: {w['class_name']})"
        )
    return "\n".join(lines)


@tool
def find_window(title: str) -> str:
    """Find a window by partial title match.

    Args:
        title: Partial window title to search for (case-insensitive).

    Returns a list of matching windows or a message if none found.
    """
    windows = list_all_windows()
    matches = [
        w for w in windows if title.lower() in w["title"].lower()
    ]
    if not matches:
        return f"No windows found matching '{title}'."

    lines = [f"Windows matching '{title}':"]
    for i, w in enumerate(matches, 1):
        lines.append(
            f"  {i}. '{w['title']}' (PID: {w['process_id']})"
        )
    return "\n".join(lines)


@tool
def connect_to_app(app_name: str, start_if_not_found: bool = True) -> str:
    """Connect to a running application or start it if not found.

    Args:
        app_name: Name of the application (e.g. 'notepad', 'calc').
            Used as both the search title and executable name.
        start_if_not_found: If True, starts the app when not found running.

    Stores the connected app in the internal registry for use by other tools.
    """
    key = app_name.lower()
    title_re = f"(?i).*{app_name}.*"

    # Check if already connected with a valid window
    if key in _app_registry:
        entry = _app_registry[key]
        if entry.get("window") is not None:
            return f"Already connected to '{app_name}'."
        # Window was None from a previous failed attempt, remove and retry
        del _app_registry[key]

    # Try to connect to running instance
    app, msg = connect_to_application(title_re=title_re)
    if app is not None:
        try:
            window = app.top_window()
            _app_registry[key] = {"app": app, "window": window}
            return f"Connected to '{app_name}'. Window: '{window.window_text()}'"
        except Exception:
            pass

    # Start the application if allowed
    if start_if_not_found:
        app, msg = start_application(app_name)
        if app is not None:
            try:
                window = app.top_window()
                _app_registry[key] = {"app": app, "window": window}
                return f"Started and connected to '{app_name}'. Window: '{window.window_text()}'"
            except Exception as e:
                return f"Started '{app_name}' but could not get window: {e}"

    return f"Could not connect to '{app_name}': {msg}"


@tool
def start_app(app_name: str) -> str:
    """Start a new instance of an application (always launches fresh).

    Args:
        app_name: Name of the application executable (e.g. 'notepad', 'calc').

    Use this instead of connect_to_app when the user explicitly says 'open'
    and you want a fresh window rather than reusing an existing one.
    """
    key = app_name.lower()

    # Remove any old registry entry so we get a fresh connection
    _app_registry.pop(key, None)

    app, msg = start_application(app_name)
    if app is None:
        return f"Could not start '{app_name}': {msg}"

    try:
        window = app.top_window()
        _app_registry[key] = {"app": app, "window": window}
        return f"Started '{app_name}'. Window: '{window.window_text()}'"
    except Exception as e:
        return f"Started '{app_name}' but could not get window: {e}"


@tool
def get_window_info(app_name: str) -> str:
    """Get detailed information about a connected application's window.

    Args:
        app_name: Name of the app (must be previously connected via connect_to_app).

    Returns window title, class name, rectangle bounds, and visibility status.
    """
    entry = _app_registry.get(app_name.lower())
    if not entry:
        return f"'{app_name}' is not connected. Use connect_to_app first."

    window = entry.get("window")
    if not window:
        return f"'{app_name}' is connected but no window reference available."

    try:
        info_lines = [
            f"Window info for '{app_name}':",
            f"  Title: {window.window_text()}",
            f"  Class: {window.friendly_class_name()}",
            f"  Rectangle: {window.rectangle()}",
            f"  Visible: {window.is_visible()}",
            f"  Enabled: {window.is_enabled()}",
        ]
        return "\n".join(info_lines)
    except Exception as e:
        return f"Error getting window info: {e}"
