# Deployments

## Branching Strategy

The following are long-running branches used in the build pipeline.

- `dev` - Used to consolidate feature branches
- `staging` - Used to preview changes before production ([staging.d1waz5kiczd3n9.amplifyapp.com](staging.d1waz5kiczd3n9.amplifyapp.com))
- `main` - Production branch ([app.proximal.energy](app.proximal.energy))

When committing to the `staging` or `main` branch, a new [AWS Amplify](https://aws.amazon.com/amplify/?nc=sn&loc=0) build process will be initiated. Builds can be monitored in the [AWS Console](https://us-east-2.console.aws.amazon.com/amplify/apps/d1waz5kiczd3n9/overview).

Branches should be created when adding new features or making modifications to existing code. If necessary, these branches can be published to GitHub and reviewed by other team members. In general, these branches should only be merged into the `dev` branch.

Note, only the `main` production branch uses the Clerk [Production application](https://dashboard.clerk.com/apps/app_2YxQ2Rradk0k293mukG3TarJT5b/instances/ins_2c30IBoVDqXeLAAjdq54CXqcmVx). When using the `staging` branch or URL, or when running any of the branches locally, the Clerk [Development application](https://dashboard.clerk.com/apps/app_2YxQ2Rradk0k293mukG3TarJT5b/instances/ins_2YxQ2UEmm19inLxYjlvNOGNyTF5) is used.
