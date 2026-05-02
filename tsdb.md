# Usernames and Passwords
tsdbadmin: XBCig@&j2F&4BfxY
services:  9oWpF!zhf5DM$Q9O
github_actions: T538R6$h8A2!KbeE

# Deployed Service Database Credentials

Most deployed runtime database credentials are stored in AWS, not GitHub
Actions secrets.

| Service | Deploy/runtime | Database credential source |
| --- | --- | --- |
| API `api-prod-v2` | Elastic Beanstalk | EB env var `DATABASE_URL` |
| API `api-staging-2` | Elastic Beanstalk | EB env var `DATABASE_URL` |
| API `api-sandbox` | Elastic Beanstalk | EB env var `DATABASE_URL` |
| API `api-demo` | Elastic Beanstalk | EB env var `DATABASE_URL` |
| Weather alerts Lambda | AWS Lambda | Secrets Manager `nws/weather/notifications` |
| Calendar reminders Lambda | AWS Lambda | Secrets Manager `calendar/reminders` |
| Data connection outage Lambda | AWS Lambda | Secrets Manager `microservices/data_connection_outage_notification` |
| Issues pipeline Lambda | AWS Lambda | Secrets Manager `microservices/issues_pipeline` |
| `pv-eem` Lambda | AWS Lambda image | `.env` copied into ECR image |
| `kpi-pipeline-lambda` | AWS Lambda image | `.env` copied into ECR image |
| `kpi-pipeline-fetcher-lambda` | AWS Lambda image | `.env` copied into ECR image |

## Masked Database Targets

| Source | Masked database target |
| --- | --- |
| All API EB envs | `postgresql://tsdbadmin@axum77lqps.bcg8pupipo.tsdb.cloud.timescale.com:32340/tsdb_transaction` |
| `nws/weather/notifications` | `postgresql://tsdbadmin@axum77lqps.bcg8pupipo.tsdb.cloud.timescale.com:38568/tsdb` |
| `calendar/reminders` | `postgresql://tsdbadmin@axum77lqps.bcg8pupipo.tsdb.cloud.timescale.com:38568/tsdb` |
| `microservices/data_connection_outage_notification` | `postgresql://tsdbadmin@axum77lqps.bcg8pupipo.tsdb.cloud.timescale.com:38568/tsdb` |
| `microservices/issues_pipeline` | `postgresql://tsdbadmin@axum77lqps.bcg8pupipo.tsdb.cloud.timescale.com:32340/tsdb_transaction` |

GitHub Actions has a repository secret named `DATABASE_URL`, but repo
references show it is used by PR/check workflows, not the deploy path.
Deploy workflows use GitHub secrets for AWS auth and webhooks, including
`AWS_ROLE_ARN_EB`, `AWS_ROLE_ARN_CODEARTIFACT`, and Amplify webhooks.

Notable concern: `pv-eem`, `kpi`, and `kpi-pipeline-fetcher` Dockerfiles copy
`.env` into the Lambda image, so those secrets live in the built ECR image
rather than Secrets Manager or Lambda environment configuration.
