# Project QC Tests

# Get QC health for Serrano project
GET {{baseURL}}/v1/operational/projects/6970fba7-6462-475f-805a-2357ee4ababb/qc/health
x-api-key: {{apiKey}}
HTTP 200

# Validate combiner data for QC
GET {{baseURL}}/v1/operational/projects/6970fba7-6462-475f-805a-2357ee4ababb/qc/combiner-swaps/validate-combiner-data
x-api-key: {{apiKey}}
[Query]
start: 2025-05-11T05:00:00.000Z
end: 2025-05-12T05:00:00.000Z
device_ids: 782
device_ids: 783
device_ids: 784
device_ids: 785
device_ids: 786
device_ids: 787
HTTP 200
