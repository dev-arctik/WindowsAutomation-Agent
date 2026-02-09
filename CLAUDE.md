# WindowsAutomation-Agent

## Project Overview
An AI-powered Windows GUI automation agent. Users give natural language commands via CLI, and the agent plans and executes GUI actions (clicks, keystrokes, menu navigation) on Windows desktop apps using pywinauto.

## Architecture
- **Framework**: LangGraph (state graphs for multi-step automation workflows)
- **LLM**: OpenAI GPT-4.1-mini via LangChain
- **GUI Backend**: pywinauto (Win32 + UIA backends)
- **CLI**: Typer for rich CLI interface
- **Config**: python-dotenv for API keys, centralized config in `config/`

## Project Structure
```
WindowsAutomation-Agent/
├── config/
│   ├── config.py          # LLM, model settings
│   └── secret_keys.py     # API key loading from .env
├── tools/
│   ├── window_tools.py    # pywinauto wrappers as LangGraph tools
│   ├── inspect_tools.py   # GUI tree inspection tools
│   └── input_tools.py     # Keyboard/mouse action tools
├── graphs/
│   ├── automation_graph.py # Main automation state graph
│   └── planner_graph.py   # Task planning sub-graph
├── utils/
│   └── gui_helpers.py     # pywinauto helper utilities
├── cli.py                 # Typer CLI entrypoint
├── pyproject.toml
├── .env.example
├── .gitignore
├── CLAUDE.md
└── README.md
```

## Key Design Decisions
- Each pywinauto action is wrapped as a LangGraph **tool** so the agent can call them
- The LangGraph state graph handles: intent parsing → app discovery → action planning → execution → verification
- Supervisor pattern routes between specialized sub-agents (window finder, action executor, verifier)
- Follows same numbered file convention as sibling projects for experiments (e.g., `001-basic_notepad.py`)

## Conventions
- **Naming**: Numbered files for experiments (`NNN-description.py`), descriptive names for core modules
- **Dependencies**: Managed via Poetry (`pyproject.toml`)
- **API keys**: Loaded from `.env` via `config/secret_keys.py` — never hardcoded
- **Python version**: 3.11+
- **Git**: Commit messages should be concise and descriptive

## Common Commands
```bash
# Setup
poetry install
cp .env.example .env  # Then add your API keys

# Run
poetry run python cli.py "open notepad and type hello world"

# Run specific experiment
poetry run python 001-basic_notepad.py
```

## Dependencies
- langgraph, langchain, langchain-openai — agent framework
- pywinauto — Windows GUI automation
- typer, rich — CLI interface
- python-dotenv — env management

## Notes
- pywinauto only works on Windows. For development on macOS, you can build/test the graph logic and mock the pywinauto calls
- Two pywinauto backends: `win32` (default, lighter) and `uia` (richer control access) — prefer `uia` for modern apps
- Always use pywinauto's built-in waits instead of `time.sleep()`
