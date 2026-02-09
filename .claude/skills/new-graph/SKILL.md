---
name: new-graph
description: Scaffold a new LangGraph state graph for an automation workflow
argument-hint: "[graph-name] [description]"
---

# Create a New LangGraph State Graph

Create a new LangGraph state graph in the `graphs/` directory for an automation workflow.

## Steps

1. Create `graphs/$ARGUMENTS[0].py` using this template:

```python
"""
$ARGUMENTS[1]
"""

from typing import TypedDict, Annotated, List, Literal

from langgraph.graph import StateGraph, START, END
from langgraph.graph import MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver

from config.config import get_llm
from config.secret_keys import OPENAI_API_KEY


# defining the LLM
llm = get_llm()


# defining the tools
# TODO: Add tools as plain functions with Google-style docstrings
# def example_tool(a: str, b: str) -> str:
#     """Description of what this tool does.
#
#     Args:
#         a: first param
#         b: second param
#     """
#     return result

# tools = [example_tool]
# llm_with_tools = llm.bind_tools(tools, parallel_tool_calls=False)


# System message
sys_msg = SystemMessage(content="You are a helpful assistant for automation tasks.")


# Node
def assistant(state: MessagesState):
    return {"messages": [llm.invoke([sys_msg] + state["messages"])]}


# Build the graph
builder = StateGraph(MessagesState)

# Define nodes: these do the work
builder.add_node("assistant", assistant)

# Define edges: these determine how the control flow moves
builder.add_edge(START, "assistant")
builder.add_edge("assistant", END)

# Compile graph with memory
memory = MemorySaver()
graph = builder.compile(checkpointer=memory)


# Specify a thread AKA session
config = {"configurable": {"thread_id": "1"}}

if __name__ == "__main__":
    # Start the conversation loop
    while True:
        user_msg = input("Enter your message (or type 'exit' to quit): ")
        if user_msg.lower() == 'exit':
            print("Exiting the session...")
            break

        messages = [HumanMessage(content=user_msg)]
        messages = graph.invoke({"messages": messages}, config)

        for m in messages['messages']:
            m.pretty_print()
```

2. Follow these patterns:
   - Use `MessagesState` for chat graphs, `TypedDict` + `Annotated` for custom state
   - Use `get_llm()` from `config.config` — never instantiate `ChatOpenAI` directly
   - Tools are plain functions with Google-style docstrings, collected in a `tools` list
   - Bind tools with `llm.bind_tools(tools)`, use `ToolNode(tools)` for tool execution
   - Use `tools_condition` from `langgraph.prebuilt` for tool routing
   - Keep node functions pure: take state, return partial state update
   - Use conditional edges for branching logic
   - Use `builder` as the `StateGraph` variable name
   - Compile with `MemorySaver()` checkpointer
   - Include `__main__` block with interactive chat loop for testing
   - Use section comments: `# defining the LLM`, `# Build the graph`, `# Define nodes`, `# Define edges`

3. Register the graph in `graphs/__init__.py` if it exists
