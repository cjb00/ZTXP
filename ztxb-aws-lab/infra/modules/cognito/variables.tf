variable "project" {
  type = string
}

variable "callback_urls" {
  description = "OAuth callback URLs for the Cognito app client"
  type        = list(string)
  default     = ["https://example.com/callback"]
}

variable "logout_urls" {
  description = "OAuth logout URLs for the Cognito app client"
  type        = list(string)
  default     = ["https://example.com/logout"]
}
