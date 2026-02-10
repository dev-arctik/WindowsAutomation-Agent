# pywinauto-mcp Development Tools Setup

## Overview
This project uses **pywinauto-mcp** as a development tool to help Claude (AI assistant) interact with Windows GUI during development. This MCP server is **NOT** part of the runtime automation - it's a development-time aid.

## What is pywinauto-mcp?
- **Location**: `D:\project_KLUTZ\pywinauto-mcp`
- **Purpose**: Allows Claude to inspect Windows UI, test pywinauto commands, and debug automations interactively
- **Version**: 0.3.1 (Portmanteau Edition)
- **Framework**: FastMCP 2.14.5
- **Agent**: `.claude/agents/mcp-helper.md` - Use this agent when developing automations

## When to Use It

### ✅ **Use pywinauto-mcp when:**
- Building new automation workflows
- Debugging why an automation fails
- Exploring new app UI structures
- Testing pywinauto commands before adding them to tools
- Inspecting control trees and element properties

### ❌ **Don't use pywinauto-mcp for:**
- Runtime automation (use LangGraph tools instead)
- Production workflows
- End-user automations

## Quick Start

### 1. Start the MCP Server
```powershell
cd D:\project_KLUTZ\pywinauto-mcp
poetry run python -m pywinauto_mcp
```

### 2. Use the MCP Helper Agent
In Claude Code, the `mcp-helper` agent will automatically have access to the MCP tools when the server is running.

### 3. Example: Explore Notepad
```
You: "I want to automate Notepad to save files"
Claude (using mcp-helper agent):
  1. automation_windows("find", title="Notepad")
  2. get_desktop_state()
  3. Tests: automation_elements("click", control_id="Save")
  4. Provides you working code for tools/notepad_tools.py
```

## Available MCP Tools

The MCP provides 8 comprehensive portmanteau tools:

### 1. `automation_windows` (11 operations)
Window management: list, find, maximize, minimize, restore, close, activate, position, rect, title, state

**Example:**
```python
automation_windows("list")                     # List all windows
automation_windows("find", title="Notepad", partial=True)
automation_windows("maximize", handle=12345)
```

### 2. `automation_elements` (14 operations)
UI element interaction: click, double_click, right_click, hover, info, text, set_text, rect, visible, enabled, exists, wait, verify_text, list

**Example:**
```python
automation_elements("click", window_handle=12345, control_id="btnOK")
automation_elements("text", window_handle=12345, control_id="Edit1")
automation_elements("set_text", window_handle=12345, control_id="Edit1", text="Hello!")
```

### 3. `automation_mouse` (9 operations)
Mouse control: position, move, move_relative, click, double_click, right_click, scroll, drag, hover

**Example:**
```python
automation_mouse("position")
automation_mouse("click", x=500, y=300)
automation_mouse("drag", x=100, y=100, target_x=500, target_y=300)
```

### 4. `automation_keyboard` (4 operations)
Keyboard input: type, press, hotkey, hold

**Example:**
```python
automation_keyboard("type", text="Hello World!")
automation_keyboard("press", key="enter")
automation_keyboard("hotkey", keys=["ctrl", "c"])
```

### 5. `automation_visual` (4 operations)
Visual operations: screenshot, extract_text (OCR), find_image, highlight

**Example:**
```python
automation_visual("screenshot")
automation_visual("extract_text", image_path="screen.png")
```

### 6. `automation_face` (5 operations)
Face recognition: add, recognize, list, delete, capture (optional - not installed)

### 7. `automation_system` (7 operations)
System utilities: health, help, wait, wait_for_window, clipboard_get, clipboard_set, process_list

**Example:**
```python
automation_system("health")
automation_system("wait", seconds=2.5)
automation_system("clipboard_get")
```

### 8. `get_desktop_state`
Comprehensive desktop UI element discovery with visual annotations and OCR

**Example:**
```python
get_desktop_state()  # Basic
get_desktop_state(use_vision=True, use_ocr=True, max_depth=15)  # Full
```

## MCP Server Configuration

### Claude Desktop Configuration
Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "pywinauto": {
      "command": "poetry",
      "args": ["run", "python", "-m", "pywinauto_mcp"],
      "cwd": "D:\\project_KLUTZ\\pywinauto-mcp"
    }
  }
}
```

## Architecture

```
Development Time:                Runtime:
┌─────────────────┐             ┌──────────────────┐
│ You + Claude    │             │ User Command     │
│ (using MCP)     │             │                  │
└────────┬────────┘             └────────┬─────────┘
         │                               │
         ▼                               ▼
  ┌──────────────┐             ┌──────────────────┐
  │ mcp-helper   │             │ LangGraph Agent  │
  │ agent        │             │ (GPT-4.1-mini)   │
  └──────┬───────┘             └────────┬─────────┘
         │                               │
         ▼                               ▼
  ┌──────────────┐             ┌──────────────────┐
  │ pywinauto-mcp│             │ Your Tools       │
  │ server       │             │ (window_tools,   │
  │ (inspect UI) │             │  input_tools,    │
  └──────────────┘             │  etc.)           │
                               └──────────────────┘
```

## Workflow Example

### Scenario: Building Excel Automation

1. **You ask Claude:**
   "Help me automate saving an Excel file"

2. **Claude (using mcp-helper agent):**
   ```python
   # Find Excel window
   automation_windows("find", title="Excel")

   # Inspect UI
   get_desktop_state()

   # Test Save button
   automation_elements("click", window_handle=12345, control_id="SaveButton")

   # Take screenshot to verify
   automation_visual("screenshot", window_handle=12345)
   ```

3. **Claude provides you working code:**
   ```python
   # tools/excel_tools.py
   @tool
   def save_excel_file(app_name: str) -> str:
       """Save the current Excel workbook."""
       registry = get_app_registry()
       entry = registry.get(app_name.lower())
       window = entry["window"]
       save_btn = window.child_window(auto_id="SaveButton", control_type="Button")
       safe_click(save_btn)
       return "Excel file saved successfully"
   ```

4. **You add it to your project:**
   - Add to `tools/excel_tools.py`
   - Register in `tools/__init__.py`
   - Use in LangGraph automation

5. **Runtime:** Your automation agent uses the tool (not MCP)

## Installation Details

- **Location**: `D:\project_KLUTZ\pywinauto-mcp`
- **Package Manager**: Poetry
- **Python Version**: 3.10+ (Python 3.12 installed)
- **Dependencies**:
  - fastmcp>=2.13.1
  - pywinauto>=0.6.8
  - pytesseract (OCR support)
  - opencv-python-headless (image processing)
  - pillow (screenshots)
  - And more... (see pyproject.toml)

## Troubleshooting

### MCP server won't start
```powershell
cd D:\project_KLUTZ\pywinauto-mcp
poetry install  # Reinstall if needed
poetry run python -m pywinauto_mcp
```

### Can't connect to MCP from Claude Desktop
1. Check `claude_desktop_config.json` paths are correct
2. Verify Poetry is in your PATH
3. Restart Claude Desktop
4. Check server logs

### Tools not working
- Ensure Windows GUI is accessible
- Check pywinauto backend (UIA vs Win32)
- Test with simple apps first (Notepad, Calculator)
- Use `automation_system("health")` to check server status

### Agent not using MCP tools
1. Ensure MCP server is running
2. Use the `mcp-helper` agent explicitly
3. Check Claude Desktop has MCP configured

## Best Practices

1. **Always test with MCP before writing tool code**
   - Don't guess control selectors
   - Use `get_desktop_state()` to find exact identifiers

2. **Translate MCP commands to LangGraph tools**
   - MCP is for testing
   - LangGraph tools are for production

3. **Use screenshots for debugging**
   - Helps understand what the user is seeing
   - `automation_visual("screenshot")`

4. **Document findings in project memory**
   - App-specific patterns
   - Control identifiers that work
   - Backend preferences

## Reference

- **MCP Server GitHub**: https://github.com/sandraschi/pywinauto-mcp
- **Main Project Tools**: `tools/` directory in this project
- **LangGraph State**: `graphs/automation_graph.py`
- **MCP Helper Agent**: `.claude/agents/mcp-helper.md`
- **pywinauto Docs**: https://pywinauto.readthedocs.io/
- **FastMCP Docs**: https://gofastmcp.com/
