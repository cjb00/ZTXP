resource "aws_kms_key" "signing" {
  description              = "${var.project} ES256 signing key"
  key_usage                = "SIGN_VERIFY"
  customer_master_key_spec = "ECC_NIST_P256"
  deletion_window_in_days  = 7
}

output "signing_key_arn" { value = aws_kms_key.signing.arn }
variable "project" { type = string }
