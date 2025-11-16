###############################################
# VPC (simple: public subnets only for lab)
###############################################

module "vpc" {
  source  = "./modules/vpc"
  project = var.project
}

###############################################
# KMS (asymmetric signing key for TAMs)
###############################################

module "kms" {
  source  = "./modules/kms"
  project = var.project
}

###############################################
# Cognito (user pool for demo users)
###############################################

module "cognito" {
  source  = "./modules/cognito"
  project = var.project
}

###############################################
# DynamoDB (notes table and optional cache)
###############################################

module "dynamodb" {
  source  = "./modules/dynamodb"
  project = var.project
}

###############################################
# S3 bucket for PDP policy bundles (optional)
###############################################

module "s3_policy_bundles" {
  source  = "./modules/s3_policy_bundles"
  project = var.project
}

###############################################
# PDP (ECS Fargate with OPA)
###############################################

module "pdp_fargate" {
  source = "./modules/pdp_fargate"

  # Core identifiers / wiring
  project           = var.project
  vpc_id            = module.vpc.vpc_id
  public_subnet_ids = module.vpc.public_subnet_ids
  default_sg_id     = module.vpc.default_sg_id

  # What the module previously complained about as required
  security_group_ids = [module.vpc.default_sg_id]
  image              = var.pdp_image
  region             = var.region
}

###############################################
# ZTXP Broker (API + Lambda)
###############################################

module "ztxp_broker" {
  source = "./modules/ztxp_broker"

  project     = var.project
  kms_key_arn = module.kms.signing_key_arn
  pdp_url     = module.pdp_fargate.pdp_url
}

###############################################
# Notes API (Demo app + PEP authorizer)
###############################################

module "api_notes" {
  source = "./modules/api_notes"

  project           = var.project
  kms_key_arn       = module.kms.signing_key_arn
  broker_invoke_url = module.ztxp_broker.invoke_url

  notes_table_name = module.dynamodb.notes_table_name
  notes_table_arn  = module.dynamodb.notes_table_arn
}
