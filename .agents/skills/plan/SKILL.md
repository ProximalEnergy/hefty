---
name: plan
description: >-
  create a plan document to break up work into manageable tasks
---

# Rules
- Do NOT write code.
- Be concise, sacrifice grammar for concision
- Use core/src/core/db_query.py for database CRUD operations
- Use `uv` not `pip`

# Step 1: Enter plan mode
- Read: user input, spec file (if given), relevant codebase sections
- Identify existing patterns and conventions
- Note risks and unknowns to user until none remain

# Step 2: Identify the Dependency Graph
- Map what depends on what:
  - DB Schema (core/src/core/models.py)
    - Seed Data/Migrations
    - Domain Logic
      - API Routes
        - Front End Changes

# Step 3: Slice into Vertical Tasks

- Bad (horizontal slicing):
  - Task 1: Build entire database schema
  - Task 2: Build all API endpoints
  - Task 3: Build all UI components
  - Task 4: Connect everything
- Good (vertical slicing):
  - Task 1: User can create an account (schema + API + UI for registration)
  - Task 2: User can log in (auth schema + API + UI for login)
  - Task 3: User can create a task (task schema + API + UI for creation)
  - Task 4: User can view task list (query + API + UI for list view)

# Step 4:  Write Tasks
- Write task description given the following format
  ```
  ## Task [N]: [Short descriptive title]
  
  **Description:** One paragraph explaining what this task accomplishes.
  
  **Acceptance criteria:**
  - [ ] [Specific, testable condition]
  - [ ] [Specific, testable condition]
  
  **Dependencies:** [Task numbers this depends on, or "None"]
  
  **Files likely touched:**
  - `src/path/to/file.ts`
  - `tests/path/to/test.ts`
  
  **Estimated scope:** [Small: 1-2 files | Medium: 3-5 files | Large: 5+ files]
  ```
- Break large tasks into small and medium tasks until there are no large tasks left

# Step 5:  Create Plan Document

# Implementation Plan: [Feature/Project Name]

## Overview
[One paragraph summary of what we're building]

## Architecture Decisions
- [Key decision 1 and rationale]
- [Key decision 2 and rationale]

## Task List

### Phase 1: Foundation
- [ ] Task 1: ...
- [ ] Task 2: ...

### Phase 2: Core Features
- [ ] Task 3: ...
- [ ] Task 4: ...

### Checkpoint: Core Features
- [ ] End-to-end flow works

### Phase 3: Polish
- [ ] Task 5: ...
- [ ] Task 6: ...

### Checkpoint: Complete
- [ ] All acceptance criteria met
- [ ] Ready for review

## Risks and Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| [Risk] | [High/Med/Low] | [Strategy] |

## Open Questions
- [Question needing human input]
