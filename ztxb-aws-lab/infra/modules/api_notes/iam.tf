###############################################
# SHARED ASSUME ROLE POLICY
###############################################

data "aws_iam_policy_document" "notes_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

###############################################
# PEP ROLE + KMS SIGN
###############################################

resource "aws_iam_role" "pep" {
  name               = "${var.project}-pep-authorizer"
  assume_role_policy = data.aws_iam_policy_document.notes_assume.json
}

resource "aws_iam_role_policy_attachment" "pep_logs" {
  role       = aws_iam_role.pep.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_policy" "kms_sign" {
  name = "${var.project}-pep-kms-sign"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["kms:Sign"]
        Resource = var.kms_key_arn
        Condition = {
          StringEquals = {
            "kms:SigningAlgorithm" = "ECDSA_SHA_256"
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "pep_kms" {
  role       = aws_iam_role.pep.name
  policy_arn = aws_iam_policy.kms_sign.arn
}

###############################################
# NOTES LAMBDA ROLE + DDB
###############################################

resource "aws_iam_role" "notes" {
  name               = "${var.project}-notes-lambda"
  assume_role_policy = data.aws_iam_policy_document.notes_assume.json
}

resource "aws_iam_role_policy_attachment" "notes_logs" {
  role       = aws_iam_role.notes.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_policy" "notes_dynamo" {
  name = "${var.project}-notes-dynamo"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
        ]
        Resource = var.notes_table_arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "notes_ddb" {
  role       = aws_iam_role.notes.name
  policy_arn = aws_iam_policy.notes_dynamo.arn
}
