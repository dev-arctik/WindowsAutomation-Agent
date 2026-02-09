"""
GUI inspection tools for the automation agent.

Tools for inspecting control trees, getting control properties,
and taking screenshots. Used by the verifier agent and for debugging.
"""

import os
from typing import Any

from langchain_core.tools import tool

from tools.window_tools import get_app_registry
from utils.gui_helpers import capture_control_tree, find_control

MAX_TREE_OUTPUT = 4000  # Truncate control tree to keep LLM context manageable


@tool
def inspect_control_tree(app_name: str, depth: int = 3) -> str:
    """Inspect the control tree of a connected application.

    Args:
        app_name: Name of the app (must be previously connected).
        depth: How many levels deep to inspect (default 3).

    Returns a text representation of the control hierarchy, truncated
    to 4000 characters to fit within LLM context.
    """
    registry = get_app_registry()
    entry = registry.get(app_name.lower())
    if not entry:
        return f"'{app_name}' is not connected. Use connect_to_app first."

    window = entry.get("window")
    if not window:
        return f"'{app_name}' has no window reference."

    tree = capture_control_tree(window, depth=depth)
    if len(tree) > MAX_TREE_OUTPUT:
        tree = tree[:MAX_TREE_OUTPUT] + "\n... (truncated)"
    return f"Control tree for '{app_name}':\n{tree}"


@tool
def get_control_properties(
    app_name: str,
    control_type: str | None = None,
    title: str | None = None,
    auto_id: str | None = None,
) -> str:
    """Get detailed properties of a specific control.

    Args:
        app_name: Name of the app (must be previously connected).
        control_type: Type of control (Button, Edit, MenuItem, etc.).
        title: Control title or label text.
        auto_id: Automation ID of the control.

    Returns control name, type, automation_id, enabled state, texts, and bounds.
    """
    registry = get_app_registry()
    entry = registry.get(app_name.lower())
    if not entry:
        return f"'{app_name}' is not connected. Use connect_to_app first."

    window = entry.get("window")
    if not window:
        return f"'{app_name}' has no window reference."

    control, msg = find_control(
        window,
        control_type=control_type,
        title=title,
        auto_id=auto_id,
    )
    if control is None:
        return f"Control not found: {msg}"

    try:
        elem = control.element_info
        lines = [
            f"Control properties:",
            f"  Name: {getattr(elem, 'name', 'N/A')}",
            f"  Type: {getattr(elem, 'control_type', 'N/A')}",
            f"  AutomationId: {getattr(elem, 'automation_id', 'N/A')}",
            f"  ClassName: {getattr(elem, 'class_name', 'N/A')}",
            f"  Enabled: {control.is_enabled()}",
            f"  Visible: {control.is_visible()}",
            f"  Texts: {control.texts()}",
            f"  Rectangle: {control.rectangle()}",
        ]
        return "\n".join(lines)
    except Exception as e:
        return f"Error reading properties: {e}"


@tool
def list_child_controls(
    app_name: str,
    control_type: str | None = None,
) -> str:
    """List child controls of a connected application's window.

    Args:
        app_name: Name of the app (must be previously connected).
        control_type: Filter by control type (Button, Edit, MenuItem, etc.).
            If None, lists all actionable control types.

    Returns a formatted list of matching controls with their names and types.
    """
    registry = get_app_registry()
    entry = registry.get(app_name.lower())
    if not entry:
        return f"'{app_name}' is not connected. Use connect_to_app first."

    window = entry.get("window")
    if not window:
        return f"'{app_name}' has no window reference."

    actionable_types = {
        "Button", "Edit", "MenuItem", "ComboBox", "ListItem",
        "TreeItem", "CheckBox", "RadioButton", "TabItem", "Hyperlink",
    }

    try:
        kwargs: dict[str, Any] = {}
        if control_type:
            kwargs["control_type"] = control_type

        children = window.children(**kwargs)
        filtered = []
        for child in children:
            try:
                ctype = child.friendly_class_name()
                if control_type or ctype in actionable_types:
                    filtered.append({
                        "title": child.window_text(),
                        "type": ctype,
                        "enabled": child.is_enabled(),
                    })
            except Exception:
                continue

        if not filtered:
            return f"No matching controls found in '{app_name}'."

        lines = [f"Controls in '{app_name}':"]
        for i, c in enumerate(filtered, 1):
            status = "enabled" if c["enabled"] else "disabled"
            lines.append(f"  {i}. [{c['type']}] '{c['title']}' ({status})")
        return "\n".join(lines)
    except Exception as e:
        return f"Error listing controls: {e}"


@tool
def take_screenshot(app_name: str, filename: str | None = None) -> str:
    """Take a screenshot of a connected application's window.

    Args:
        app_name: Name of the app (must be previously connected).
        filename: Optional filename to save the screenshot.
            Defaults to 'tmp/{app_name}_screenshot.png'.

    Returns the file path where the screenshot was saved.
    """
    registry = get_app_registry()
    entry = registry.get(app_name.lower())
    if not entry:
        return f"'{app_name}' is not connected. Use connect_to_app first."

    window = entry.get("window")
    if not window:
        return f"'{app_name}' has no window reference."

    try:
        os.makedirs("tmp", exist_ok=True)
        if not filename:
            filename = f"tmp/{app_name.lower()}_screenshot.png"

        image = window.capture_as_image()
        if image is None:
            return "Screenshot capture returned None (Pillow may not be installed)."

        image.save(filename)
        return f"Screenshot saved to: {filename}"
    except Exception as e:
        return f"Screenshot failed: {e}"
