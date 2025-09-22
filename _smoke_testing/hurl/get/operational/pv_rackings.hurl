# PV Rackings Tests

# Get PV rackings by ID
GET {{baseURL}}/v1/operational/pv-rackings
x-api-key: {{apiKey}}
[Query]
racking_ids: 1
HTTP 200
[Asserts]
status == 200

# Get PV racking manufacturers
GET {{baseURL}}/v1/operational/pv-rackings/manufacturers
x-api-key: {{apiKey}}
HTTP 200
[Asserts]
status == 200

# Get PV racking models by manufacturer
GET {{baseURL}}/v1/operational/pv-rackings/models
x-api-key: {{apiKey}}
[Query]
manufacturer: NexTracker
HTTP 200
[Asserts]
status == 200

# Lookup PV racking IDs by manufacturers and models
GET {{baseURL}}/v1/operational/pv-rackings/lookup-ids
x-api-key: {{apiKey}}
[Query]
manufacturers: NexTracker
manufacturers: Nevados
models: Horizon
models: TRACE
HTTP 200
[Asserts]
status == 200
