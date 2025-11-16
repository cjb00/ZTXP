resource "aws_dynamodb_table" "decisions" {
  name         = "${var.project}-ztxp-decisions"
  billing_mode = "PAY_PER_REQUEST"

  hash_key = "tam_hash"

  attribute {
    name = "tam_hash"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }
}

output "decisions_table_name" {
  value = aws_dynamodb_table.decisions.name
}
