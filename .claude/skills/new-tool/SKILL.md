---
name: new-tool
description: Scaffold a new LangGraph tool that wraps a pywinauto action
argument-hint: "[tool-name] [description]"
disable-model-invocation: true
---

# Create a New LangGraph Tool

Create a new pywinauto action wrapped as a LangGraph tool in the `tools/` directory.

## Steps

1. Determine which tools file this belongs in:
   - `tools/window_tools.py` — window management (find, connect, list, focus)
   - `tools/input_tools.py` — keyboard and mouse actions (click, type, scroll)
   - `tools/inspect_tools.py` — GUI tree inspection (dump controls, find elements)
   - If none fit, create a new file following the naming pattern

2. Create the tool using this template:

```python
from langchain_core.tools import tool
from pywinauto import Application


@tool
def $ARGUMENTS[0](target: str) -> str:
    """$ARGUMENTS[1]

    Args:
        target: Description of the target parameter

    Returns:
        Result description
    """
    try:
        # pywinauto implementation here
        app = Application(backend='uia').connect(title=target)
        window = app.window(title=target)
        window.wait('ready', timeout=10)

        # Perform the action
        # ...

        return f"Successfully performed action on {target}"
    except Exception as e:
        return f"Error: {str(e)}"
```

3. Follow these conventions:
   - Use the `@tool` decorator from `langchain_core.tools`
   - Always include a docstring — LangGraph uses it as the tool description for the LLM
   - Return strings (success messages or error descriptions)
   - Use `backend='uia'` by default, document if `win32` is needed
   - Always use `wait()` instead of `time.sleep()`
   - Wrap in try/except and return error strings (don't raise)
   - Add type hints to all parameters

4. Register the tool in the appropriate graph by adding it to the tools list

5. Add a brief test or usage example as a comment
