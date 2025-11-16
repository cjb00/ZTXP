#!/usr/bin/env bash
# app/pdp/scripts/build.sh

set -euo pipefail

REGION="${1:-us-east-1}"
REPO_NAME="ztxp-pdp"

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"

# Ensure repo exists
aws ecr describe-repositories \
  --repository-names "${REPO_NAME}" \
  --region "${REGION}" >/dev/null 2>&1 || \
aws ecr create-repository \
  --repository-name "${REPO_NAME}" \
  --region "${REGION}" >/dev/null

IMAGE_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${REPO_NAME}:latest"

# Login to ECR
aws ecr get-login-password --region "${REGION}" \
  | docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

# Build and push
docker build -t "${IMAGE_URI}" .
docker push "${IMAGE_URI}"

echo
echo "PDP image pushed:"
echo "  ${IMAGE_URI}"
