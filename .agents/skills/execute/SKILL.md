---
name: execute
description: >-
  Write code that adheres to a given plan
---

# Rules
- code lines are shorter than 88 characters
- write descriptive function names
- Do not ignore knip, mypy, or ruff failures. Fix them.
- always use ripgrep instead of grep
- Do not make code changes outside of task scope

# Step 1
- Read the plan document and implement user's desired task number
- Ask for task number if not given
