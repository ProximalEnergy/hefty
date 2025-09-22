# Device Types Tests

# Get all device types
GET {{baseURL}}/v1/operational/device_types
x-api-key: {{apiKey}}
HTTP 200
[Asserts]
status == 200

# Get device type by ID
GET {{baseURL}}/v1/operational/device_types/1
x-api-key: {{apiKey}}
HTTP 200
[Asserts]
status == 200
jsonpath "$.name_short" == "project"
