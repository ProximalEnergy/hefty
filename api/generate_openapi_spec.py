import json

from app.main import app  # Make sure this import points to your FastAPI app instance

# --- Final Recommended Script ---

# 1. Manually clear any cached OpenAPI schema.
# This is the most robust way to guarantee that FastAPI rebuilds the schema
# from scratch, respecting all your latest Pydantic v2 model configurations.
app.openapi_schema = None

# 2. Call the standard .openapi() method to generate the fresh schema.
openapi_schema = app.openapi()

# 3. Write the schema to your openapi.json file.
output_path = "openapi.json"
with open(output_path, "w") as f:
    json.dump(openapi_schema, f, indent=2)

print(f"✅ Fresh OpenAPI schema successfully generated at: {output_path}")
