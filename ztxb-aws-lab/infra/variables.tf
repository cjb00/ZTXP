variable "project" {
  description = "Project name prefix for all resources"
  type        = string
  default     = "ztxp-aws-lab"
}

variable "region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "pdp_image" {
  description = "ECR image URI for the PDP (OPA) container"
  type        = string
  default     = "" # set via -var or tfvars (e.g. from build.sh output)
}

variable "tags" {
  description = "Default tags applied to resources"
  type        = map(string)
  default = {
    project = "ztxp-aws-lab"
  }
}
