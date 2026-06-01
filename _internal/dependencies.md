# Dependencies

## General Notes
- Dependency upgrades are monitored by `renovate`

---------------------------------
## High Risk

### Polars
- Polars does not follow semantic versioning so upgrading is risky
- Tips:
  - Ask AI to do sentiment analysis on github issues for new releases
  - lower number patch versions are riskier


---------------------------------

## Low Risk

### FastAPI
- FastAPI is managed by renovate only in the `api` repository.  It also needs to be upgrade in the `core` `dev dependencies`, but that should be done by a human.



----------------------------------
