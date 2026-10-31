# ADR 007: Migration from CloudFormation to Terraform

## Status
Accepted

## Context
Previously, application infrastructure was defined using three separate CloudFormation templates (`infra/auth.yml`, `infra/reports.yml`, `infra/ai.yml`). While functional, CloudFormation is limited to AWS and makes cross-provider management difficult.

## Decision
We migrated all infrastructure management to Terraform and HCP Terraform.
- Multi-provider capabilities for future expansion.
- State management and remote execution via HCP Terraform with OIDC authentication.
- Zero-downtime resource adoption using Terraform `import` blocks.

## Consequences
- CloudFormation templates deleted.
- Declarative state stored in HCP Terraform.
- Automatic plan and apply triggered on GitHub commits.
