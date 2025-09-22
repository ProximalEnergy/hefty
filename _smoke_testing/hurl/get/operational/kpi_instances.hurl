# KPI Instances Tests

# Get all KPI instances
GET {{baseURL}}/v1/operational/kpi-instances/
x-api-key: {{apiKey}}
HTTP 200
[Asserts]
status == 200
jsonpath "$" isCollection
