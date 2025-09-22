# CEC PV Modules Tests

# Get CEC PV modules by ID
GET {{baseURL}}/v1/operational/cec-pv-modules/
x-api-key: {{apiKey}}
[Query]
cec_pv_module_ids: 1767
HTTP 200
[Asserts]
status == 200

# Get CEC PV module in proximal format
GET {{baseURL}}/v1/operational/cec-pv-modules/proximal-format
x-api-key: {{apiKey}}
[Query]
cec_pv_module_id: 5378
HTTP 200
[Asserts]
status == 200
