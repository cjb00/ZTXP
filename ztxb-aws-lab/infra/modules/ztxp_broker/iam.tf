###############################################
# IAM ROLE FOR ZTXP BROKER LAMBDA
###############################################

data "aws_iam_policy_document" "broker_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "broker_lambda" {
  name               = "${var.project}-broker-lambda"
  assume_role_policy = data.aws_iam_policy_document.broker_assume.json
}

###############################################
# BASIC EXECUTION PERMISSIONS
###############################################

resource "aws_iam_role_policy_attachment" "broker_logs" {
  role       = aws_iam_role.broker_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

###############################################
# KMS VERIFY PERMISSIONS
###############################################

resource "aws_iam_policy" "kms_verify" {
  name = "${var.project}-broker-kms-verify"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["kms:Verify"]
        Resource = var.kms_key_arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "broker_kms" {
  role       = aws_iam_role.broker_lambda.name
  policy_arn = aws_iam_policy.kms_verify.arn
}
