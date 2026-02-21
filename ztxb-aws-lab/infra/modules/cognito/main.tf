###############################################
# USER POOL
###############################################

resource "aws_cognito_user_pool" "this" {
  name = "${var.project}-pool"

  schema {
    attribute_data_type = "String"
    name                = "email"
    required            = true
    mutable             = true
  }

  auto_verified_attributes = ["email"]

  # cognito:groups is included automatically in the ID token
  # when a user belongs to one or more groups
}

###############################################
# USER POOL GROUPS
# These map directly to the OPA policy groups:
#   "writer" → can create/update notes
#   "admin"  → full access
###############################################

resource "aws_cognito_user_group" "writer" {
  user_pool_id = aws_cognito_user_pool.this.id
  name         = "writer"
  description  = "Users who can create and update notes"
}

resource "aws_cognito_user_group" "admin" {
  user_pool_id = aws_cognito_user_pool.this.id
  name         = "admin"
  description  = "Administrators with full access"
}

###############################################
# APP CLIENT
###############################################

resource "aws_cognito_user_pool_client" "app" {
  name         = "${var.project}-app-client"
  user_pool_id = aws_cognito_user_pool.this.id

  generate_secret = false

  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["email", "openid", "profile"]
  allowed_oauth_flows_user_pool_client = true

  callback_urls                = var.callback_urls
  logout_urls                  = var.logout_urls
  supported_identity_providers = ["COGNITO"]
}

###############################################
# OUTPUTS
###############################################

output "user_pool_id" {
  value = aws_cognito_user_pool.this.id
}

output "user_pool_arn" {
  value = aws_cognito_user_pool.this.arn
}

output "app_client_id" {
  value = aws_cognito_user_pool_client.app.id
}
