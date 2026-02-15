###############################################
# PACKAGE BROKER LAMBDA
###############################################

data "archive_file" "ztxp_broker_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../../app/lambdas/ztxp_broker"
  output_path = "${path.module}/ztxp_broker.zip"
}

resource "aws_lambda_function" "broker" {
  function_name = "${var.project}-ztxp-broker"
  handler       = "handler.lambda_handler"
  runtime       = "python3.12"
  role          = aws_iam_role.broker_lambda.arn
  filename      = data.archive_file.ztxp_broker_zip.output_path

  timeout = 5

  environment {
    variables = {
      PDP_URL     = var.pdp_url
      KMS_KEY_ARN = var.kms_key_arn
    }
  }
}

###############################################
# HTTP API FOR BROKER
###############################################

resource "aws_apigatewayv2_api" "broker_http" {
  name          = "${var.project}-ztxp-broker-api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "broker_lambda" {
  api_id                 = aws_apigatewayv2_api.broker_http.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.broker.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "broker_evaluate" {
  api_id    = aws_apigatewayv2_api.broker_http.id
  route_key = "POST /ztxp/evaluate"
  target    = "integrations/${aws_apigatewayv2_integration.broker_lambda.id}"
}

resource "aws_apigatewayv2_stage" "broker_default" {
  api_id      = aws_apigatewayv2_api.broker_http.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "broker_invoke" {
  statement_id  = "AllowAPIGatewayInvokeBroker"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.broker.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.broker_http.execution_arn}/*/*"
}

###############################################
# VARIABLES
###############################################

variable "project" {
  type = string
}

variable "kms_key_arn" {
  type = string
}

variable "pdp_url" {
  type = string
}

###############################################
# OUTPUTS
###############################################

output "invoke_url" {
  value = aws_apigatewayv2_api.broker_http.api_endpoint
}
