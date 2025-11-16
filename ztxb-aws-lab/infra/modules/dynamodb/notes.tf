resource "aws_dynamodb_table" "notes" {
  name         = "${var.project}-notes"
  billing_mode = "PAY_PER_REQUEST"

  hash_key  = "user_id"
  range_key = "note_id"

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "note_id"
    type = "S"
  }
}

output "notes_table_name" {
  value = aws_dynamodb_table.notes.name
}

output "notes_table_arn" {
  value = aws_dynamodb_table.notes.arn
}
