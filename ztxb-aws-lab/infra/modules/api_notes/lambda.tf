###############################################
# NOTES LAMBDA
###############################################

data "archive_file" "notes_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../../app/lambdas/notes_api"
  output_path = "${path.module}/notes.zip"
}

resource "aws_lambda_function" "notes" {
  function_name = "${var.project}-notes-api"
  handler       = "handler.lambda_handler"
  runtime       = "python3.12"
  role          = aws_iam_role.notes.arn
  filename      = data.archive_file.notes_zip.output_path

  environment {
    variables = {
      TABLE_NAME = var.notes_table_name
    }
  }
}

###############################################
# PEP LAMBDA (CUSTOM AUTHORIZER)
###############################################

data "archive_file" "pep_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../../app/lambdas/pep_authorizer"
  output_path = "${path.module}/pep.zip"
}

resource "aws_lambda_function" "pep" {
  function_name = "${var.project}-pep-authorizer"
  handler       = "handler.lambda_handler"
  runtime       = "python3.12"
  role          = aws_iam_role.pep.arn
  filename      = data.archive_file.pep_zip.output_path

  environment {
    variables = {
      KMS_KEY_ARN = var.kms_key_arn
      BROKER_URL  = var.broker_invoke_url
    }
  }
}
