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

## Development Tools

### pywinauto-mcp (Debugging Only)
MCP server for interactive Windows GUI automation. **Only use for debugging and verification, NOT for runtime automation.**

- **Location**: `D:\project_KLUTZ\pywinauto-mcp`
- **Agent**: `.claude/agents/mcp-helper.md`
- **Docs**: `MCP_SETUP.md`

**When to use pywinauto-mcp:**
- Verifying CLI automation results (did Notepad actually get the text? Did Calculator show the right answer?)
- Inspecting control trees to find correct auto_ids and control names
- Debugging failures (take screenshots, list windows, check element states)
- Testing new pywinauto patterns before adding them to tools/

**When NOT to use pywinauto-mcp:**
- DO NOT use it as the primary automation — `cli.py` is the product, MCP is the debugger
- DO NOT replace CLI testing with direct MCP automation

**Debugging workflow:**
1. Run `cli.py run "your command"` via Bash
2. Use `automation_windows("list")` to verify the app launched
3. Use `automation_elements("list", ...)` or `automation_visual("screenshot")` to verify results
4. Use `automation_windows("manage", handle=..., action="restore")` to bring windows to foreground before screenshots
5. If something failed, use `automation_elements("list", ..., max_depth=5)` to find correct control identifiers

**Important MCP quirks:**
- Always bring windows to foreground with `manage→restore` before interacting
- Use `automation_visual("screenshot")` for desktop-level screenshots (window-level can fail)
- All MCP tool permissions should be in `.claude/settings.local.json` to avoid focus-stealing approval dialogs

## Known Windows 11 Quirks
- **Notepad restores tabs**: Win11 Notepad restores previous session tabs on launch. The planner always adds `Ctrl+N` after `start_app("notepad")` to open a clean new tab.
- **Calculator auto_ids**: Use `num0Button`..`num9Button`, `plusButton`, `minusButton`, `multiplyButton`, `divideButton`, `equalButton`, `clearButton`, etc. NEVER use digit titles like "7" — use auto_ids.
- **UWP/WinUI3 apps**: Modern Windows apps use launcher processes that don't match the final window PID. `start_application()` in `gui_helpers.py` handles this with polling and handle-based detection.

## Graph Architecture Details
The automation graph uses a **supervisor pattern** with retry logic:
- `supervisor` → deterministic routing (no LLM) based on state
- `intent_parser` → calls planner sub-graph for structured action plan
- `action_executor` → LLM picks tools to execute each step (with full context)
- `step_result_checker` → inspects tool results for error patterns, retries up to 2x per step
- `verifier` → inspects final app state with inspect tools
- Error patterns checked: "not connected", "Control not found", "timed out", "failed:", etc.
- Max 30 iterations before forced stop
