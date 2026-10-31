# ADR 007: Migration from CloudFormation to Terraform

## Status
Accepted

## Context
Infrastructure was defined in three CloudFormation templates (`auth.yml`,
`reports.yml`, `ai.yml`). They worked, but CloudFormation is limited to AWS,
and the project already reaches outside one AWS account and will need more
than one environment.

## Decision
We manage all infrastructure with Terraform, with state and runs in
HCP Terraform (workspace `spry-dev`, working directory `infra`).
Existing resources were adopted with `import` blocks, not re-created.

### Why Terraform, not the alternatives
- CloudFormation: AWS-only, no single plan-first workflow across providers.
- CDK: still AWS-only and still deploys through CloudFormation underneath.
- OpenTofu: compatible with our files and a valid fallback if the BSL
  licence becomes a problem. Terraform was chosen because HCP Terraform
  is what the course and our workspace use.

### Who can change infrastructure, and how
Changes go through Git: commit to `main`, then HCP Terraform plans and
applies (auto-apply for VCS runs). No one needs AWS keys: HCP Terraform
gets short-lived credentials through OIDC. The Makefile only plans
(`make infra-plan`); it never applies.

### Secrets and state
No secrets are committed. `terraform.tfvars` holds non-secret values only;
sensitive values live in workspace variables. State files are git-ignored.
State is stored in HCP Terraform and may contain resource attributes, so
workspace access must be treated as sensitive.

### If HCP Terraform is down
Running infrastructure is not affected; only changes are blocked.
In an emergency the workspace can be switched to Local execution and
applied with personal credentials, then switched back.

## Consequences
- CloudFormation templates deleted.
- Declarative state stored in HCP Terraform.
- Automatic plan and apply triggered on GitHub commits.
- Drift is visible in every plan; manual console changes will be reverted.
- The team now owns state protection and workspace access.
