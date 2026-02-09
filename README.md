# WindowsAutomation-Agent

AI-powered Windows desktop automation using natural language commands. Built with LangGraph + pywinauto.

## What it does

You type a command in plain English, the AI agent figures out the steps and executes them on your Windows desktop:

```bash
python cli.py run "open notepad and type hello world"
python cli.py run "in chrome, go to github.com"
python cli.py run "open calculator and compute 255 * 37"
```

The agent uses a **supervisor pattern** to orchestrate the workflow:
1. **Intent Parser** — analyzes your command and creates a structured step-by-step plan
2. **Window Finder** — locates or starts the target application
3. **Action Executor** — executes each planned step (clicks, keystrokes, menu navigation)
4. **Verifier** — confirms each action succeeded before moving on

## Tech Stack

- **LangGraph** — stateful agent workflow orchestration (supervisor + sub-graphs)
- **pywinauto** — Windows GUI automation (UIA backend by default)
- **OpenAI GPT-4.1-mini** — intent parsing, action planning, tool calling
- **Typer + Rich** — CLI interface with formatted output
- **Pydantic** — structured output models for planning

## Setup

### Prerequisites
- Python 3.11+
- [Poetry](https://python-poetry.org/docs/#installation)
- Windows OS (required for actual GUI automation; macOS/Linux work for development with mock layer)

### Installation

```bash
# Clone the repo
git clone https://github.com/dev-arctik/WindowsAutomation-Agent.git
cd WindowsAutomation-Agent

# Install dependencies
poetry install

# On Windows, also install pywinauto
poetry install --extras windows

# Copy env template and add your OpenAI API key
cp .env.example .env
# Edit .env and set OPENAI_API_KEY=sk-...
```

### API Key

You need an [OpenAI API key](https://platform.openai.com/api-keys). Add it to your `.env` file:

```
OPENAI_API_KEY=your_openai_api_key_here
```

## Usage

### CLI Commands

```bash
# Run an automation command
poetry run python cli.py run "open notepad and type hello world"

# Run with verbose output (shows all LLM messages)
poetry run python cli.py run "open calc" --verbose

# List all visible windows
poetry run python cli.py list-windows

# Inspect an app's control tree (useful for development)
poetry run python cli.py inspect notepad
```

### Experiments

Numbered experiment files test specific automation scenarios:

```bash
# Full graph mode — agent plans and executes autonomously
poetry run python 001-basic_notepad.py

# Direct mode — calls tools without the graph (for testing tools)
poetry run python 001-basic_notepad.py --direct

# Custom command
poetry run python 001-basic_notepad.py --command "open notepad and type testing 123"
```

## Project Structure

```
WindowsAutomation-Agent/
├── config/
│   ├── __init__.py
│   ├── config.py          # LLM factory (get_llm → ChatOpenAI)
│   └── secret_keys.py     # API key loading from .env
├── tools/
│   ├── __init__.py        # Exports all_tools, window_tools, inspect_tools, input_tools
│   ├── window_tools.py    # list_windows, find_window, connect_to_app, get_window_info
│   ├── inspect_tools.py   # inspect_control_tree, get_control_properties, list_child_controls, take_screenshot
│   └── input_tools.py     # click_element, type_text, press_keys, select_item, menu_select
├── graphs/
│   ├── __init__.py        # Exports build_automation_graph, build_planner_graph
│   ├── planner_graph.py   # Task planning sub-graph (structured output → ActionPlan)
│   └── automation_graph.py # Main supervisor graph (routes between sub-agents)
├── utils/
│   ├── __init__.py
│   └── gui_helpers.py     # pywinauto abstraction + mock layer for macOS/Linux
├── cli.py                 # Typer CLI entrypoint
├── 001-basic_notepad.py   # First experiment: Notepad automation
├── pyproject.toml         # Poetry config
├── .env.example           # Environment variable template
├── CLAUDE.md              # AI coding assistant instructions
└── README.md
```

## Architecture

```
User Command (CLI)
       │
       ▼
┌─────────────┐
│  Supervisor  │ ◄── routes between agents, max 20 iterations
└──────┬──────┘
       │
  ┌────┼────┬──────────┐
  ▼    ▼    ▼          ▼
Intent  Window  Action   Verifier
Parser  Finder  Executor
  │      │       │        │
  │      │       │        │
  ▼      ▼       ▼        ▼
Planner  Window  All     Inspect
SubGraph Tools   Tools   Tools
```

Each sub-agent has its own tool-calling loop (LLM → ToolNode → LLM) and returns control to the supervisor when done.

## Development on macOS/Linux

pywinauto only works on Windows, but you can develop and test the graph logic on any OS. The `utils/gui_helpers.py` module provides mock classes (`_MockApp`, `_MockWindow`, `_MockDesktop`, `_MockControl`) that replicate the pywinauto API surface with `[MOCK]` print messages.

```bash
# This works on macOS — uses mock layer
poetry run python cli.py list-windows
# Output: mock window list

poetry run python 001-basic_notepad.py --direct
# Output: mock tool calls with [MOCK] prefixes
```

## Tools Reference

| Tool | Description |
|------|-------------|
| `list_windows()` | List all visible desktop windows |
| `find_window(title)` | Find window by partial title match |
| `connect_to_app(app_name, start_if_not_found)` | Connect to or start an application |
| `get_window_info(app_name)` | Get window title, class, bounds, visibility |
| `inspect_control_tree(app_name, depth)` | Dump the GUI control hierarchy |
| `get_control_properties(app_name, ...)` | Get control name, type, automation_id, etc. |
| `list_child_controls(app_name, control_type)` | List actionable child controls |
| `take_screenshot(app_name, filename)` | Screenshot the app window |
| `click_element(app_name, ...)` | Click a UI element |
| `type_text(app_name, text, ...)` | Type text into a control or window |
| `press_keys(app_name, keys)` | Press keyboard keys (pywinauto syntax) |
| `select_item(app_name, item_text, ...)` | Select item in list/combo/tree |
| `menu_select(app_name, menu_path)` | Navigate menus (e.g. `"File->Save"`) |
