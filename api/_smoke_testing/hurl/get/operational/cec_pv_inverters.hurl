# CEC PV Inverters Tests

# Get CEC PV inverters by ID
GET {{baseURL}}/v1/operational/cec-pv-inverters/
x-api-key: {{apiKey}}
[Query]
cec_pv_inverter_ids: 1
HTTP 200
[Asserts]
status == 200
