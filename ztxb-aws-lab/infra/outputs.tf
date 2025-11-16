###############################################
# PUBLIC ENDPOINTS
###############################################

output "notes_api_url" {
  description = "Base URL of the protected Notes API"
  value       = module.api_notes.api_url
}

output "broker_api_url" {
  description = "Base URL of the ZTXP Broker API"
  value       = module.ztxp_broker.invoke_url
}

output "pdp_url" {
  description = "DNS name / URL of the PDP (OPA) endpoint"
  value       = module.pdp_fargate.pdp_url
}

###############################################
# IDENTITY
###############################################

output "cognito_user_pool_id" {
  description = "Cognito User Pool ID (for creating test users)"
  value       = module.cognito.user_pool_id
}

output "cognito_user_pool_arn" {
  description = "Cognito User Pool ARN"
  value       = module.cognito.user_pool_arn
}

###############################################
# DEBUG / INFRA STRUCTURE
###############################################

output "vpc_id" {
  description = "VPC ID for the lab"
  value       = module.vpc.vpc_id
}
