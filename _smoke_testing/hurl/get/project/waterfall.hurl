# Project Waterfall Tests

# Get project waterfall data for device_type level (default)
GET {{baseURL}}/v1/operational/projects/6970fba7-6462-475f-805a-2357ee4ababb/waterfall/
x-api-key: {{apiKey}}
HTTP 200
[Asserts]
status == 200
jsonpath "$.value" not isEmpty
jsonpath "$.measure" not isEmpty
jsonpath "$.name" not isEmpty
jsonpath "$.value" isCollection
jsonpath "$.measure" isCollection
jsonpath "$.name" isCollection
