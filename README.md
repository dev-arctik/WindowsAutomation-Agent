# WindowsAutomation-Agent

AI-powered Windows desktop automation using natural language commands. Built with LangGraph + pywinauto.

## What it does

You type a command in plain English, the AI agent figures out the steps and executes them on your Windows desktop:

```bash
python cli.py "open notepad and type hello world"
python cli.py "in chrome, go to github.com"
python cli.py "open calculator and compute 255 * 37"
```

## Tech Stack

- **LangGraph** — stateful agent workflow orchestration
- **pywinauto** — Windows GUI automation (Win32 + UIA backends)
- **OpenAI GPT-4.1-mini** — intent parsing and action planning
- **Typer + Rich** — CLI interface

## Setup

### Prerequisites
- Python 3.11+
- Poetry
- Windows OS (pywinauto requires Windows for GUI automation)

### Installation

```bash
# Install dependencies
poetry install

# Copy env template and add your API keys
cp .env.example .env
```

### Usage

```bash
# Run a command
poetry run python cli.py "your natural language command here"

# Run experiments
poetry run python 001-basic_notepad.py
```

## Project Structure

```
├── config/           # LLM and API key configuration
├── tools/            # pywinauto action wrappers as LangGraph tools
├── graphs/           # LangGraph state graphs for automation workflows
├── utils/            # Helper utilities
├── cli.py            # CLI entrypoint
└── NNN-*.py          # Numbered experiment files
```
