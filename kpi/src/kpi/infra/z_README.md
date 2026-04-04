
# Infra

All the messy non-domain logic goes here. This section is primarily functional (instead of based on classes). 
This is where database connections, crud operations, and io operations are handled.

Ideally, this is the only code that explicitly imports from non enum `core`.

Depends on:
- `base/`
- `core`

Does not depend on:
- `domain/`
- `service/`
- `workflow/`

