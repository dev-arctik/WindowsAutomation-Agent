"""
Input action tools for the automation agent.

Tools for clicking, typing, pressing keys, selecting items,
and navigating menus in Windows applications.
"""

from typing import Any

from langchain_core.tools import tool

from tools.window_tools import get_app_registry
from utils.gui_helpers import find_control, safe_click, safe_type


@tool
def click_element(
    app_name: str,
    control_type: str | None = None,
    title: str | None = None,
    auto_id: str | None = None,
) -> str:
    """Click a UI element in a connected application.

    Args:
        app_name: Name of the app (must be previously connected).
        control_type: Type of control to click (Button, MenuItem, etc.).
        title: Control title or label text.
        auto_id: Automation ID of the control.

    At least one of control_type, title, or auto_id must be provided
    to identify the target control.
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

    result = safe_click(control)
    return result


@tool
def type_text(
    app_name: str,
    text: str,
    control_type: str | None = None,
    title: str | None = None,
    auto_id: str | None = None,
    use_set_text: bool = False,
) -> str:
    """Type text into a control or the active window.

    Args:
        app_name: Name of the app (must be previously connected).
        text: Text to type. Supports pywinauto key syntax
            (e.g. '{ENTER}', '^s' for Ctrl+S).
        control_type: Type of control to type into (e.g. 'Edit').
        title: Control title or label text.
        auto_id: Automation ID of the control.
        use_set_text: If True, uses set_text() instead of type_keys().
            Faster but doesn't trigger key events.

    If no control identifiers are provided, types into the window directly.
    """
    registry = get_app_registry()
    entry = registry.get(app_name.lower())
    if not entry:
        return f"'{app_name}' is not connected. Use connect_to_app first."

    window = entry.get("window")
    if not window:
        return f"'{app_name}' has no window reference."

    # If control identifiers provided, find the specific control
    if any([control_type, title, auto_id]):
        control, msg = find_control(
            window,
            control_type=control_type,
            title=title,
            auto_id=auto_id,
        )
        if control is None:
            return f"Control not found: {msg}"
        target = control
    else:
        target = window

    try:
        if use_set_text:
            target.set_text(text)
            return f"Set text on '{app_name}' successfully."
        else:
            result = safe_type(target, text)
            return result
    except Exception as e:
        return f"Type failed: {e}"


@tool
def press_keys(app_name: str, keys: str) -> str:
    """Press keyboard keys in a connected application.

    Args:
        app_name: Name of the app (must be previously connected).
        keys: Key sequence using pywinauto syntax. Examples:
            - '{ENTER}' for Enter key
            - '^s' for Ctrl+S
            - '%{F4}' for Alt+F4
            - '^a' for Ctrl+A (select all)
            - '{TAB}' for Tab key

    Sends keystrokes to the application's main window.
    """
    registry = get_app_registry()
    entry = registry.get(app_name.lower())
    if not entry:
        return f"'{app_name}' is not connected. Use connect_to_app first."

    window = entry.get("window")
    if not window:
        return f"'{app_name}' has no window reference."

    try:
        result = safe_type(window, keys)
        return f"Pressed keys '{keys}' in '{app_name}'. {result}"
    except Exception as e:
        return f"Key press failed: {e}"


@tool
def select_item(
    app_name: str,
    item_text: str,
    control_type: str | None = None,
    title: str | None = None,
    auto_id: str | None = None,
) -> str:
    """Select an item in a list, combo box, or tree control.

    Args:
        app_name: Name of the app (must be previously connected).
        item_text: Text of the item to select.
        control_type: Type of the container control
            (ComboBox, ListBox, TreeView, etc.).
        title: Control title or label text.
        auto_id: Automation ID of the control.
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
        control.select(item_text)
        return f"Selected '{item_text}' in '{app_name}'."
    except Exception as e:
        return f"Selection failed: {e}"


@tool
def menu_select(app_name: str, menu_path: str) -> str:
    """Navigate and select a menu item.

    Args:
        app_name: Name of the app (must be previously connected).
        menu_path: Menu path using '->' separator.
            Examples: 'File->Save', 'File->Save As', 'Edit->Find'.
    """
    registry = get_app_registry()
    entry = registry.get(app_name.lower())
    if not entry:
        return f"'{app_name}' is not connected. Use connect_to_app first."

    window = entry.get("window")
    if not window:
        return f"'{app_name}' has no window reference."

    try:
        window.menu_select(menu_path)
        return f"Selected menu '{menu_path}' in '{app_name}'."
    except Exception as e:
        return f"Menu selection failed: {e}"
