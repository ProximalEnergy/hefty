# PV Modules Tests

# Get PV module IDs by manufacturer and company
GET {{baseURL}}/v1/operational/pv-modules/ids/
x-api-key: {{apiKey}}
[Query]
pv_module_manufacturer: Longi
pv_module_manufacturer: First Solar
company_id: 01959294-3e51-4d3e-9f57-e9c2c3635c84
HTTP 200
[Asserts]
status == 200

# Get PV module manufacturers
GET {{baseURL}}/v1/operational/pv-modules/manufacturers
x-api-key: {{apiKey}}
HTTP 200
[Asserts]
status == 200

# Get PV module models by manufacturer
GET {{baseURL}}/v1/operational/pv-modules/models
x-api-key: {{apiKey}}
[Query]
manufacturer: Longi
HTTP 200
[Asserts]
status == 200
