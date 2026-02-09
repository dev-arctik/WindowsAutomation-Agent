---
name: review-graph
description: Review a LangGraph state graph for correctness, missing edges, state schema issues, and best practice violations
argument-hint: "[graph-file-path]"
context: fork
agent: Explore
allowed-tools: Read, Grep, Glob
---

# Review LangGraph State Graph

Thoroughly review the LangGraph state graph in `$ARGUMENTS` for issues.

## Review Checklist

### 1. State Schema
- [ ] All fields in TypedDict are used by at least one node
- [ ] Accumulator fields use `Annotated[..., operator.add]`
- [ ] No mutable defaults (use `None` and set in nodes)
- [ ] Status field has clear enum-like values documented

### 2. Node Functions
- [ ] Each node takes state and returns a partial dict update
- [ ] No side effects beyond the intended action
- [ ] Error handling doesn't swallow exceptions silently
- [ ] Return values match the state schema types

### 3. Edge Connections
- [ ] `START` connects to an entry node
- [ ] Every node has at least one outgoing edge
- [ ] All conditional edge return values map to valid node names
- [ ] `END` is reachable from every path
- [ ] No orphaned nodes (unreachable from START)
- [ ] No infinite loops without a max-iteration guard

### 4. Tool Integration
- [ ] All tools used by the graph are registered in the tools list
- [ ] Tool functions have proper docstrings (LLM uses these)
- [ ] Tool return types are strings
- [ ] Tools handle errors and return error messages instead of raising

### 5. pywinauto Specifics
- [ ] No `time.sleep()` calls — use pywinauto waits instead
- [ ] Backend specified explicitly (`uia` or `win32`)
- [ ] Window connections use `wait('ready')` after connecting
- [ ] Controls verified as enabled before interaction

### 6. Best Practices
- [ ] Graph has a `build_graph()` factory function
- [ ] `__main__` block for standalone testing
- [ ] LLM model loaded from config, not hardcoded
- [ ] API keys loaded from `config/secret_keys.py`, never hardcoded

## Output

Provide findings organized by severity:
- **Critical**: Will cause runtime errors or incorrect behavior
- **Warning**: May cause issues in edge cases
- **Suggestion**: Improvement for maintainability or robustness

Include the specific file location and a code fix for each finding.
