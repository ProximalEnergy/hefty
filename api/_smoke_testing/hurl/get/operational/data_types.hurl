# Data Types Tests

# Get all data types
GET {{baseURL}}/v1/operational/data-types
x-api-key: {{apiKey}}
HTTP 200
[Asserts]
status == 200

# Get data type by ID
GET {{baseURL}}/v1/operational/data-types/1
x-api-key: {{apiKey}}
HTTP 200
[Asserts]
status == 200
jsonpath "$.data_type_id" isNumber
