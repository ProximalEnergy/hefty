# KPI Types Tests

# Get KPI type by name
GET {{baseURL}}/v1/operational/kpi-types/by-name/pv_inverter_mechanical_availability
x-api-key: {{apiKey}}
HTTP 200
[Asserts]
status == 200
jsonpath "$" not isEmpty
jsonpath "$.kpi_type_id" isNumber

# Get all KPI types
GET {{baseURL}}/v1/operational/kpi-types/
x-api-key: {{apiKey}}
HTTP 200
[Asserts]
status == 200
jsonpath "$[0].kpi_type_id" isNumber

# Get KPI type by ID
GET {{baseURL}}/v1/operational/kpi-types/1
x-api-key: {{apiKey}}
HTTP 200
[Asserts]
status == 200
jsonpath "$.kpi_type_id" == 1
jsonpath "$.name_short" not isEmpty

# Get KPI types by project ID
GET {{baseURL}}/v1/operational/kpi-types/by-project/b102379c-eadb-4cc4-808b-a3d4b3f3ea5a
x-api-key: {{apiKey}}
HTTP 200
[Asserts]
status == 200
jsonpath "$[0].kpi_type_id" isNumber
