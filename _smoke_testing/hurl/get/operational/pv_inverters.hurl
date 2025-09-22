# PV Inverters Tests

# Get PV inverters by ID
GET {{baseURL}}/v1/operational/pv-inverters
x-api-key: {{apiKey}}
[Query]
inverter_ids: 0
HTTP 200
[Asserts]
status == 200

# Get PV inverter manufacturers
GET {{baseURL}}/v1/operational/pv-inverters/manufacturers
x-api-key: {{apiKey}}
HTTP 200
[Asserts]
status == 200

# Get PV inverter models by manufacturer
GET {{baseURL}}/v1/operational/pv-inverters/models
x-api-key: {{apiKey}}
[Query]
manufacturer: Sungrow
HTTP 200
[Asserts]
status == 200

# Get inverter IDs by manufacturer
GET {{baseURL}}/v1/operational/pv-inverters/ids
x-api-key: {{apiKey}}
[Query]
inverter_manufacturer: Sungrow
HTTP 200
[Asserts]
status == 200
