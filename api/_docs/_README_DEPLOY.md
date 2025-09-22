# Notes for Deployment

## Staging
Deployments to staging are done via github actions and are triggered by `pushes` to the staging branch.  The action can be found in `.github.workflows.deploy-staging.yml`

The staging enviornment has a different set of username and password requirements than the production and local versions of the application.  Reach out to a team-mate to get these credentials.

## Production
Deployments to production are done via github actrions and are triggered `git tag` on the main branch.  The action can be found int `.github.workflows.deploy-prod.yml`.

### Caveats
The version in `pyproject.toml` must match the version in git tag.  For example `v0.1.1`.


## DNS & CNAMES
In order to make a CNAME work with HTTPS a few steps need to be completed:
- Issue a certificate from AWS Certificate Manager
- Assign that certificate to port 443 via Elastic Beanstalk
- Add the certificate name and value to namecheap

### Caveats
Namecheap UI is horrible and will freeze if you do any of these steps incorrectly.
- Copy the CNAME value from AWS to namecheap
- Manually type the name _name.subdomain in namecheap
- Hit save
- Edit the _name section of the name in namecheap with the real CNAME name
