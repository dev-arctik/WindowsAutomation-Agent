---
name: new-experiment
description: Scaffold a new numbered experiment file for testing automation workflows
argument-hint: "[description]"
disable-model-invocation: true
---

# Create a New Experiment File

Create a numbered experiment file following the project's `NNN-description.py` convention.

## Steps

1. Find the next available experiment number:
   - List existing `NNN-*.py` files in the project root
   - Increment the highest number by 1
   - Pad to 3 digits (e.g., `001`, `002`, `010`)

2. Create the experiment file using this template:

```python
"""
Experiment $0: [Brief description]

Goal: [What this experiment tests or demonstrates]
Target App: [Which Windows application]
Expected Result: [What should happen]
"""

import os
from dotenv import load_dotenv

load_dotenv()

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END

from config.config import MODEL_NAME
from config.secret_keys import OPENAI_API_KEY


def main():
    """Run the experiment."""
    print(f"--- Experiment: $0 ---")

    # Setup
    llm = ChatOpenAI(
        model=MODEL_NAME,
        api_key=OPENAI_API_KEY,
    )

    # TODO: Implement experiment logic

    print("--- Experiment Complete ---")


if __name__ == "__main__":
    main()
```

3. Naming conventions:
   - Use lowercase with underscores for the description part
   - Keep descriptions short but descriptive
   - Examples: `001-basic_notepad.py`, `002-chrome_navigation.py`, `003-calculator_math.py`

4. Each experiment should:
   - Have a clear docstring explaining the goal
   - Be self-contained and runnable with `poetry run python NNN-description.py`
   - Import from project modules (config, tools, graphs) where possible
   - Print clear output about what it's doing and the result
