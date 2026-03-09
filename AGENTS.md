# General
- code lines are shorter than 88 characters

# Plans
- Make the plan extremely concise. Sacrifice grammar for the sake of concision.
- At the end of the plan, give me a list of unresolved questions to answer, if any.

# Testing
- if Environment Variable AGENT_ENVIRONMENT == async-offline:
  - verify with `mise run check`
- else:
  - Do not verify, human will perform verification

# --- Languages ---
## Python
- use uv not pip
- Functions with arguments should use * as the first argument except when:
  - function has only self as an argument 
  - function is a fastapi route
  
## Typescript
- prefer mantine over custom css
