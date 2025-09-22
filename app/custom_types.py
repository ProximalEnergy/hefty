import uuid
from typing import Annotated

from fastapi import Query
from pydantic.json_schema import SkipJsonSchema

# Annotated type definition for deep query parameter, used in many endpoints
AnnotatedDeep = Annotated[bool, Query(description="Load all related objects.")]

# Type definition for optional list of ints
# SkipJsonSchema is used to assist with OpenAPI schema generation
# https://github.com/tiangolo/fastapi/discussions/10654
OptionalListOfInts = list[int] | SkipJsonSchema[None]

# Type definition for optional list of UUIDs
# SkipJsonSchema is used to assist with OpenAPI schema generation
# https://github.com/tiangolo/fastapi/discussions/10654
OptionalListOfUUIDs = list[uuid.UUID] | SkipJsonSchema[None]
