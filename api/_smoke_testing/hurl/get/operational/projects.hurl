# Projects Tests

# Get project by ID
GET {{baseURL}}/v1/operational/projects/b102379c-eadb-4cc4-808b-a3d4b3f3ea5a
x-api-key: {{apiKey}}
HTTP 200
[Asserts]
status == 200
jsonpath "$" not isEmpty

# Get all projects
GET {{baseURL}}/v1/operational/projects
x-api-key: {{apiKey}}
HTTP 200
[Asserts]
status == 200
jsonpath "$" not isEmpty

# Get projects (alternative call)
GET {{baseURL}}/v1/operational/projects
x-api-key: {{apiKey}}
HTTP 200
[Asserts]
status == 200
jsonpath "$" not isEmpty

# Get project types
GET {{baseURL}}/v1/operational/project-types
x-api-key: {{apiKey}}
HTTP 200

# Get projects by status
GET {{baseURL}}/v1/operational/projects
x-api-key: {{apiKey}}

HTTP 200
[Asserts]
status == 200
jsonpath "$" not isEmpty
