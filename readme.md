# Project Context: EC2 Redis → AWS ElastiCache Migration (EMS-31718)

## What This Is

This is an ongoing infrastructure migration project to move a self-managed Redis instance running on EC2 to AWS ElastiCache. The work is being done using Terraform and Terragrunt as the IaC tooling. The current focus is the **Dev environment**. Prod will follow after Dev is validated.

-----

## Jira Reference

- Parent ticket: EMS-31439
- This ticket: **EMS-31718** — “Ensure Redis → ElastiCache migration pre-requirements are met”

-----

## Key People

- **Joe** — Lead DevOps / Cloud Infrastructure Engineer driving this migration
- **Marcelo (Sanchez)** — App owner and developer managing the application that connects to Redis. He inherited the app and has limited knowledge of some internal config details (e.g. CONFIG calls, AOF). He is the person to loop in for cutover and post-migration validation.

-----

## Current Redis Setup

### Dev Environment

- **EC2 Instance**: USAWA2DAPLMS01
- **Redis version**: 6.2.6 (server). Note: the redis-cli binary on the instance is version 2.8.7 — this is just the client tool, not the server
- **Port**: 6379
- **Redis binary path**: `/home/c01815a/Enterprise/bin/redis-server` (non-standard install path, not in $PATH)
- **Redis CLI path**: `/home/c01815a/Enterprise/bin/redis-cli`
- **Mode**: Standalone (Cluster Mode Disabled)
- **Replicas**: None
- **Auth**: No password, no TLS
- **Database**: Default DB0 only
- **Keys**: 27,078 keys, all with no TTL/expiry set (expires=0) — all keys are valid and active, no stale data
- **Memory usage**: 18.56MB — small dataset
- **Eviction policy**: noeviction
- **Persistence**: AOF enabled — but confirmed by Marcelo to be left on by default, not intentional
- **Custom modules**: None
- **Lua scripts**: None
- **Deprecated commands**: None detected — command set is clean for Redis 7.x migration
- **CONFIG calls**: 109 recorded in cmdstat — Marcelo is unaware of what these are, likely a Redis client library calling CONFIG GET on startup. Needs code-level investigation to confirm ElastiCache compatibility
- **EC2 instance has its own Security Group** — this SG may already define inbound/outbound rules relevant to Redis. The ElastiCache SG configuration should reference or align with this existing SG

### Prod Environment

- **EC2 Instance**: USAWA2PAPLMS03
- **Redis version**: 6.2.1 (as reported by Marcelo — not yet independently verified via INFO all)
- **Port**: 6380 (non-standard)
- **Status**: Not yet investigated in detail — Dev is the current focus

-----

## Application & Data Context

- The application connecting to Redis does **not rebuild the cache on its own** — if Redis is wiped, things break. Full data migration is required.
- **Data sources**: Most data comes from the **Umbrella database** (separate AWS account). Some data comes from **client management**. Because of the mixed sources, a full RDB snapshot migration is the safest approach — a fresh reload from Umbrella alone would not capture the client management data.
- **Endpoint config**: The Redis endpoint is stored in a **configuration XML file** within the application — not an environment variable or Secrets Manager. Cutover will require updating this XML file and doing a deployment. Marcelo confirmed downtime is minimal and negligible.
- **AWS account**: Both the EC2 Redis instances and the ElastiCache cluster will be in the **same AWS account and same VPC** — no cross-account or cross-VPC connectivity concerns for Redis itself.
- **Umbrella DB**: Lives in a separate AWS account but the app already connects to it successfully today — no new connectivity work needed post-migration.

-----

## Migration Approach Decided

- **Method**: RDB snapshot migration
- **Steps**:
1. Trigger BGSAVE on EC2 Redis to generate a fresh .rdb snapshot
1. Upload the .rdb file to an S3 bucket
1. Provision ElastiCache via Terraform/Terragrunt using `snapshot_arns` to seed the cluster on creation
1. Remove `snapshot_arns` from Terragrunt inputs after the first successful apply
1. Update the Redis endpoint in the application XML config file to point to the ElastiCache primary endpoint
1. Deploy the application
1. Validate — confirm cache hits/misses, check app logs for errors
1. Decommission EC2 Redis once stable

-----

## ElastiCache Target Configuration (Dev)

- **Engine**: Redis 7.x (latest — agreed with Marcelo to use latest on both Dev and Prod)
- **Cluster Mode**: Disabled (matches current standalone setup)
- **Node type**: cache.t3.micro (Dev)
- **Port**: 6379
- **Auth/TLS**: Disabled initially to match current setup — should be revisited for Prod
- **Encryption at rest**: Enabled
- **Eviction policy**: noeviction (matching current EC2 Redis config)
- **AOF**: Not applicable — ElastiCache does not support AOF. Post-migration durability relies on ElastiCache automated backups
- **Subnet**: Private subnets within the same VPC
- **Security Group**: To be configured referencing the existing EC2 instance SGs (USAWA2DAPLMS01 for Dev, USAWA2PAPLMS03 for Prod) as these may already define the relevant Redis access rules

-----

## IaC Structure

- **Tooling**: Terraform (modules) + Terragrunt (environment orchestration)
- **Module created**: `modules/elasticache/` containing:
  - `main.tf` — ElastiCache replication group, subnet group, security group, parameter group
  - `variables.tf` — all input variables with descriptions and defaults
  - `outputs.tf` — primary endpoint, port, replication group ID, SG ID, subnet group name, parameter group name
  - `README.md` — full module documentation including migration steps, inputs/outputs table, and important notes
- **Terragrunt env config**: `envs/dev/elasticache/terragrunt.hcl` with dependencies on VPC and app modules
- **Dependency note**: The `dependency "app"` path in terragrunt.hcl is a placeholder — the correct path depends on the actual Terragrunt Dev env folder structure, which needs to be confirmed. The dependency is needed to obtain the app’s security group ID so only the app tier can reach ElastiCache on port 6379.

-----

## Outstanding Items

1. **CONFIG calls investigation** — 109 CONFIG calls recorded against Redis. Marcelo doesn’t know what these are. Needs a code-level check to identify which CONFIG subcommands the app or its Redis client library is using, and whether ElastiCache’s CONFIG restrictions will cause any issues
1. **XML config file** — the exact file path and parameter name for the Redis endpoint needs to be located in the app codebase so the cutover change is clearly defined
1. **App module Terragrunt path** — the correct dependency path for the app module needs to be confirmed from the existing Terragrunt Dev env structure to wire up the security group dependency correctly
1. **EC2 instance SG review** — the existing SGs on USAWA2DAPLMS01 (Dev) and USAWA2PAPLMS03 (Prod) should be reviewed before finalising the ElastiCache SG rules, as they may already define relevant Redis access patterns
1. **Prod investigation** — once Dev is validated, the same pre-requirement investigation needs to be done for USAWA2PAPLMS03 (Prod, port 6380, Redis 6.2.1)

-----

## What Has Been Done So Far

- Full Redis INFO dump obtained from Dev EC2 instance (USAWA2DAPLMS01)
- Redis version, port, memory, keyspace, persistence, replication, cluster mode, eviction policy, command stats all verified
- No deprecated commands, no custom modules, no Lua scripts confirmed
- Data sources and migration requirement confirmed with Marcelo
- RDB snapshot migration approach decided
- Terraform module and Terragrunt config drafted for Dev ElastiCache provisioning
- variables.tf, outputs.tf, main.tf and README.md created for the elasticache module
