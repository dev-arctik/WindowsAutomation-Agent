# 001 - Initial Setup & Runtime Fixes

**Date**: 2026-02-09
**Status**: Resolved

---

## Summary

First full audit of the WindowsAutomation-Agent codebase. Identified and fixed 8 bugs preventing the project from running end-to-end on Windows 11.

---

## Issues Fixed

### 1. Poetry install fails — "No file/folder found for package"

**File**: `pyproject.toml`
**Root cause**: Poetry 2.x tries to install the project as a distributable package by default. This project is a standalone app, not a library.
**Fix**: Added `[tool.poetry] package-mode = false` to `pyproject.toml`.

```toml
[tool.poetry]
package-mode = false
```

---

### 2. `list-windows` shows method objects instead of PIDs

**File**: `utils/gui_helpers.py` — `list_all_windows()`
**Root cause**: On pywinauto's UIA backend, `process_id` is a **method** (not a property). `getattr(w, "process_id", None)` returns the bound method object instead of calling it.

**Before**:
```python
"process_id": getattr(w, "process_id", None),
```

**After**:
```python
pid = getattr(w, "process_id", None)
if callable(pid):
    pid = pid()
```

---

### 3. OpenAI API rejects structured output schema

**Files**: `graphs/planner_graph.py`, `graphs/automation_graph.py`
**Root cause**: The `ActionStep.tool_args` field is typed as `dict`. OpenAI's strict structured output requires `additionalProperties: false` on all object types, which plain `dict` doesn't satisfy.

**Error**:
```
BadRequestError: Invalid schema for response_format 'ActionPlan':
In context=('properties', 'tool_args'), 'additionalProperties' is required
```

**Fix**: Changed `with_structured_output()` to use `method="function_calling"` which is more permissive:
```python
structured_llm = llm.with_structured_output(ActionPlan, method="function_calling")
```

---

### 4. Message ordering crashes OpenAI API

**File**: `graphs/automation_graph.py`
**Root cause**: Slicing `state["messages"][-N:]` can cut in the middle of a tool call/response pair, leaving orphaned `ToolMessage`s without their preceding `AIMessage` (which has the `tool_calls` field). OpenAI rejects this.

**Error**:
```
messages with role 'tool' must be a response to a preceeding message with 'tool_calls'
```

**Fix**:
- Supervisor now uses `_non_tool_messages()` to filter out all `ToolMessage` and tool-calling `AIMessage` objects (it only needs high-level context for routing decisions).
- Sub-agents (action_executor, verifier) send the full message history instead of slicing.

```python
def _non_tool_messages(messages):
    return [m for m in messages
            if not isinstance(m, ToolMessage)
            and not (isinstance(m, AIMessage) and getattr(m, "tool_calls", None))]
```

---

### 5. Windows 11 Notepad — process connection fails

**File**: `utils/gui_helpers.py` — `start_application()`
**Root cause**: Windows 11's modern Notepad is a WinUI app that uses a **launcher process**. `app.start("notepad")` captures the launcher's PID, which immediately exits. The actual Notepad window runs under a different PID. `WaitForInputIdle` also fails for modern apps.

**Error**:
```
RuntimeWarning: Application is not loaded correctly (WaitForInputIdle failed)
```

**Fix**: Rewrote `start_application()` to:
1. Record existing matching window PIDs before starting
2. Launch via `subprocess.Popen()` instead of `app.start()`
3. Wait 3 seconds for the window to appear
4. Find the NEW window (PID not in the pre-existing set)
5. Connect by PID, with fallback to "Untitled" title matching

```python
subprocess.Popen(executable)
time.sleep(3)
# Find new window by comparing PIDs before/after
for w in desktop_after.windows():
    if pid not in existing_pids:
        app.connect(process=pid, timeout=15)
```

---

### 6. Agent connects to wrong Notepad window

**File**: `tools/window_tools.py`
**Root cause**: `connect_to_app` uses a regex `.*notepad.*` to find running instances. When multiple Notepad windows exist (e.g., one with unsaved work), it connects to the first match instead of opening a fresh instance.

**Fix**: Added a new `start_app` tool that always launches a fresh instance. Updated the planner prompt to distinguish:
- `start_app` — user says "open" (wants a new window)
- `connect_to_app` — user says "in notepad" (wants existing window)

---

### 7. Agent stuck in infinite supervisor loop

**File**: `graphs/automation_graph.py`
**Root cause**: The `window_finder` node only had window tools (no typing tools). After opening Notepad, it told the supervisor "I can't type." The supervisor then re-routed to `window_finder` or re-planned, creating an infinite loop.

**Fix**: Removed `window_finder` from the graph entirely. The `action_executor` already has ALL tools and follows the plan step-by-step (including `start_app` as step 1). Simplified the supervisor to a strict decision tree:

```
1. total_steps = 0       -> INTENT_PARSER
2. current_step < total  -> ACTION_EXECUTOR
3. all steps done        -> VERIFIER
4. verified              -> COMPLETE
```

---

### 8. LLM calls multiple tools simultaneously

**File**: `graphs/automation_graph.py` — `action_executor()`
**Root cause**: GPT-4.1-mini generated tool calls for multiple steps at once (e.g., `type_text` before `start_app` finished). The `ToolNode` executed them in order, but `type_text` ran before the app was registered.

**Fix**: Made the action_executor prompt extremely explicit:
```
"Call EXACTLY the tool '{tool_name}' with the given arguments.
Do NOT call any other tools. Make exactly ONE tool call."
```

---

### 9. Window not focused before typing/clicking

**File**: `utils/gui_helpers.py` — `safe_type()`, `safe_click()`
**Root cause**: pywinauto doesn't auto-focus windows. Typing into an unfocused window silently fails or sends keystrokes to the wrong target.

**Fix**: Added `set_focus()` before `type_keys()` and `click_input()`:
```python
if hasattr(control, "set_focus"):
    control.set_focus()
```

---

## Files Modified

| File | Changes |
|------|---------|
| `pyproject.toml` | Added `package-mode = false` |
| `utils/gui_helpers.py` | Fixed `process_id` callable, rewrote `start_application()`, added `set_focus()` |
| `tools/window_tools.py` | Rewrote `connect_to_app`, added `start_app` tool |
| `tools/__init__.py` | Added `start_app` to exports and tool lists |
| `graphs/planner_graph.py` | Fixed structured output method, updated planner prompt |
| `graphs/automation_graph.py` | Removed window_finder, fixed message handling, simplified supervisor |

## Result

The agent now successfully:
1. Plans automation steps from natural language
2. Opens a fresh Notepad window (even with other Notepad instances running)
3. Types text into it
4. Verifies the text appeared
5. Completes with status COMPLETE
