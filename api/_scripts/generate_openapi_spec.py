"""
Generate the OpenAPI schema for the API.
"""

import json

from app.main import app

# Clear the cached schema
app.openapi_schema = None

# Generate the fresh schema
openapi_schema = app.openapi()

# Write the schema to file
output_path = "openapi.json"
with open(output_path, "w") as f:
    json.dump(openapi_schema, f, indent=2)
