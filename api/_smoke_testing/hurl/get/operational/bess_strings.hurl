# BESS Strings Tests

GET {{baseURL}}/v1/operational/bess-strings
x-api-key: {{apiKey}}
[Query]
device_model_ids: 62
HTTP 200
[Asserts]
status == 200
