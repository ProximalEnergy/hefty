# KPI Data Tests

# Get KPI data with date range
GET {{baseURL}}/v1/operational/kpi-data
x-api-key: {{apiKey}}
[Query]
start: 2025-03-01
end: 2025-03-03
HTTP 200
