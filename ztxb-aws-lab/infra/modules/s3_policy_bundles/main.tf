resource "aws_s3_bucket" "bundles" {
  bucket = "${var.project}-policy-bundles-${random_id.sfx.hex}"
}
resource "random_id" "sfx" { byte_length = 4 }
output "bucket_name" { value = aws_s3_bucket.bundles.id }
variable "project" { type = string }
