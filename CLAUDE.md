# CLAUDE.md

## Project Overview

ZTXP (Zero Trust eXchange Protocol) is a vendor-neutral, cryptographically verifiable protocol for exchanging signed Trust Assertion Messages (TAMs) between Zero Trust Architecture components. The repo contains the protocol specification, a Python reference implementation, and an AWS lab with Terraform infrastructure.

## Repository Structure

```
spec/                        # Protocol specification (draft-ztxp-02.md)
reference/                   # Python reference implementation (ztxpv0.2.py)
ztxb-aws-lab/
  infra/                     # Terraform IaC (modular)
    modules/                 # vpc, kms, cognito, dynamodb, s3_policy_bundles,
                             # pdp_fargate, api_notes, ztxp_broker
  app/
    lambdas/                 # Python 3.12 Lambda handlers (notes_api, pep_authorizer, ztxp_broker)
    pdp/                     # OPA container (Dockerfile, Rego policies, build scripts)
docs/                        # Flow diagrams (WIP)
```

## Tech Stack

- **Spec**: Markdown (RFC-style)
- **Reference impl**: Python 3.x, Flask >=3.0.0, cryptography >=42.0.0, pyyaml >=6.0.0
- **Crypto**: Ed25519/Ed448 signing, AWS KMS (ECC_NIST_P256)
- **Infrastructure**: Terraform >=1.5.0, AWS (Lambda, API Gateway v2, ECS Fargate, DynamoDB, Cognito, KMS)
- **Policy engine**: Open Policy Agent v0.64.1, Rego
- **Containers**: Docker, AWS ECR
- **Lambda runtime**: Python 3.12

## Architecture

The ZTXP decision flow:

```
Client → Cognito Auth → API Gateway → PEP Lambda (signs TAM via KMS)
  → ZTXP Broker Lambda → OPA PDP (verifies signature, evaluates Rego policy)
  → Decision {allow|deny} → Notes API Lambda → DynamoDB
```

Core components:
- **PEP** (Policy Enforcement Point): Collects identity/device context, signs TAM
- **Broker**: Forwards signed TAMs to PDP
- **PDP** (Policy Decision Point): Verifies TAM signatures, evaluates authorization policy via OPA

## Key Commands

### Reference Implementation
```bash
# Generate Ed25519 keypair (stored in ~/.ztxp/)
python reference/ztxpv0.2.py keygen

# Sign a TAM
python reference/ztxpv0.2.py sign input.yaml output.json

# Verify a signed TAM
python reference/ztxpv0.2.py validate signed.json

# Run broker server
python reference/ztxpv0.2.py broker --host 0.0.0.0 --port 8080
```

### AWS Lab Infrastructure
```bash
cd ztxb-aws-lab/infra
terraform init
terraform plan
terraform apply
```

### PDP Container
```bash
cd ztxb-aws-lab/app/pdp/scripts
./build.sh    # Build Docker image and push to ECR
```

## Code Conventions

- Spec changes go in `spec/`, code in `reference/`
- Infrastructure is modular Terraform — each module has `main.tf`, `variables.tf`, `outputs.tf`, `iam.tf`
- Lambda handlers follow stub pattern: log event, return response (real logic TBD)
- TAM canonicalization: UTF-8, sorted JSON keys, no whitespace
- License: Apache 2.0

## Current State

- Specification: Draft-02
- Reference implementation: Functional minimal toolkit (261 lines)
- AWS lab: Infrastructure skeleton with stub Lambda handlers
- Tests: No test suite yet
- CI/CD: Not yet implemented
