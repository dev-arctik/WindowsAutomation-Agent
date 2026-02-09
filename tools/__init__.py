"""
LangGraph tools for Windows GUI automation.

All tools are plain Python functions with Google-style docstrings.
They return strings so the LLM can interpret the results.
"""

from tools.window_tools import list_windows, find_window, connect_to_app, get_window_info
from tools.inspect_tools import inspect_control_tree, get_control_properties, list_child_controls, take_screenshot
from tools.input_tools import click_element, type_text, press_keys, select_item, menu_select

# All tools collected for binding to LLM
all_tools = [
    # Window management
    list_windows,
    find_window,
    connect_to_app,
    get_window_info,
    # GUI inspection
    inspect_control_tree,
    get_control_properties,
    list_child_controls,
    take_screenshot,
    # Input actions
    click_element,
    type_text,
    press_keys,
    select_item,
    menu_select,
]

# Subsets for specialized agents
window_tools = [list_windows, find_window, connect_to_app, get_window_info]
inspect_tools = [inspect_control_tree, get_control_properties, list_child_controls, take_screenshot]
input_tools = [click_element, type_text, press_keys, select_item, menu_select]
