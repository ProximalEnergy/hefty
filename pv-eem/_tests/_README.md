# Testing Procedure

## General

## Stages
- **Stage 1:  Does the thing even run?**
  - Change `.env` `ENVIRONMENT` to `DEV`
  - Run simulation locally `uv run src/main.py`

- **Stage 2:  Do tests pass?**
  - `pytest -s`

- **Stage 3:  Does it run in docker?**
  - `docker compose -f .docker-compose.yml up --build`
  - Hit the exposed port at `:9000` with a request

## Validation
Validation tests are a different type of test to make sure that the model is performing as expected relative to a different source of truth, whether that be measured data or modeled data from a different simulation tool.

## Useful Commands
- `python -m ipykernel install --user --name myenv --display-name "Python (myenv)"` if you are using zed and want to use the REPL
