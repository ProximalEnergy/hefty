
# Domain

Contains general and industry domain logic. The code should be primarily functional (rather than class based)
and xarray functions should deal primarily with `xr.DataArray`'s rather than `xr.Dataset`'s. Leave the 
logic for extracting data arrays and assigning data arrays to `service/`.

There will still be a good deal of domain logic in `workflow/` but any heavily repeated logic should
find its way to this folder to keep the code DRY.

Depends on:
- `core.enumerations`
- `base/`

Does not depend on:
- `infra`
- `service`
- `workflow`
- `core` (besides enums)

