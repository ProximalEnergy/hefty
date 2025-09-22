# PV Expected Energy Tests

# Get PV expected energy plot data for Serrano project
GET {{baseURL}}/v1/protected/6970fba7-6462-475f-805a-2357ee4ababb/pv-expected-energy/plot
x-api-key: {{apiKey}}
[Query]
device_id: 2
start: 2025-05-20T10:00:00-05:00
end: 2025-05-20T10:30:00-05:00
HTTP 200
[Asserts]
status == 200
jsonpath "$.parent_devices" not isEmpty
jsonpath "$.times" not isEmpty
jsonpath "$.actual.power" not isEmpty
jsonpath "$.expected_soiled.power" not isEmpty
jsonpath "$.poa" not isEmpty
jsonpath "$.soiling" not isEmpty

# Get PV expected energy health for Serrano project
GET {{baseURL}}/v1/protected/6970fba7-6462-475f-805a-2357ee4ababb/pv-expected-energy/health
x-api-key: {{apiKey}}
HTTP 200
[Asserts]
status == 200
