---
name: coding-agent-workflow
description: Enforce planning and tool execution workflow for coding tasks.
---

# Coding Agent Workflow

You are a coding agent operating inside a local workspace.

## Planning Rule

Before starting any multistep task:

1. Create a task plan using `todo_write`.
2. Break the work into executable steps.
3. Track progress through the todo list.
4. Update task status as work progresses.

Never start executing a complex task before creating a plan.

---

## Tool Usage Rule

Tools must be used whenever an action is required.

### bash

Use `bash` when:

- Running shell commands
- Inspecting directories
- Executing programs
- Performing system operations

Never output shell commands as plain text.

Incorrect:

```text
ls -la