# General
- code lines are shorter than 88 characters 

# Operation Mode
- Sync/Interactive Mode:  Do not run checks
- Async/Offline Mode:  Verify changes by running _scripts/run_checks.sh --offline

# Python
- use uv not pip
- Functions with arguments should use * as the first argument except when:
  - function has only self as an argument 
  - function is a fastapi route
  
# Typescript
- prefer mantine over custom css
