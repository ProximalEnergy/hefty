# Base

This section of the code is reserved for interface defining only. There should be no
implementations as this is reserved for:
- Enums
- Protocols
- Exception and warning types
- Super light-weight related functions

It should not depend on `core` except for enums from core, and it 
should not depend on anything from `domain`, `infra`, `service`, or `workflow`.
