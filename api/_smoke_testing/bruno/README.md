# Smoke Testing
Smoke Testing which uses the Bruno application.  The goal of smoke testing is just to see if api routes are working.

## Useful commands
- `brew install --cask bruno`

## Getting to know Bruno
- Bruno authenticates by inheriting the api key from the top level collection (you may need to configure in the Auth section):
  - Key: x-api-key
  - Value: your-api-key
  - Add To: Header

## Future
- We could write API tests inside of bruno
- We could write github actions which use bruno-cli
