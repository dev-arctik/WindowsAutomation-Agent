---
name: debug-automation
description: Debug a failing automation workflow — diagnose pywinauto errors, graph execution issues, control identification failures, and timing problems
argument-hint: "[error-or-file]"
---

# Debug Automation Workflow

Systematically diagnose and fix automation failures.

## Debugging Checklist

### 1. Identify the Error Category

- **Control not found**: pywinauto can't find the target element
- **Timeout**: Wait condition never satisfied
- **Backend mismatch**: Wrong pywinauto backend for the app
- **State error**: LangGraph state corruption or missing fields
- **LLM error**: Bad tool call or malformed response
- **Permission error**: UAC or access denied

### 2. Control Not Found

```python
# Dump the control tree to see what's available
from pywinauto import Application
app = Application(backend='uia').connect(title='App Name')
app.window().print_control_identifiers()
```

Common fixes:
- Switch backend: `backend='uia'` vs `backend='win32'`
- Use `best_match` instead of exact title
- Use `child_window(control_type='Button', title_re='.*Save.*')` for regex matching
- Check if control is inside a sub-dialog or tab

### 3. Timing Issues

```python
# Add explicit waits
window.wait('ready', timeout=15)
control.wait('visible', timeout=10)
control.wait('enabled', timeout=10)
```

Never use `time.sleep()`. If waits don't work:
- Increase timeout values
- Wait for a different condition (exists → visible → ready)
- Check if a modal dialog is blocking

### 4. Graph Execution Issues

```python
# Add state logging to nodes
def my_node(state):
    print(f"State entering node: {state}")
    # ... logic ...
    result = {"status": "complete"}
    print(f"State update: {result}")
    return result
```

Common graph issues:
- Missing state field in TypedDict
- Conditional edge returning invalid node name
- Infinite loop between nodes (add max iteration check)
- Tool not registered in the graph's tool list

### 5. Diagnosis Steps

Read the error in `$ARGUMENTS` and:
1. Check if it's a pywinauto error (ElementNotFoundError, TimeoutError)
2. Check if it's a LangGraph error (InvalidUpdateError, NodeNotFoundError)
3. Check if it's an LLM error (tool call parsing, rate limit)
4. Reproduce the issue with a minimal script
5. Apply the fix and verify
