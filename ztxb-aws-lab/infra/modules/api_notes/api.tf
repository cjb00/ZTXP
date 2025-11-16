###############################################
# HTTP API FOR NOTES
###############################################

resource "aws_apigatewayv2_api" "notes_http" {
  name          = "${var.project}-notes-api"
  protocol_type = "HTTP"
}

###############################################
# CUSTOM REQUEST AUTHORIZER (PEP)
###############################################

resource "aws_apigatewayv2_authorizer" "pep" {
  api_id                            = aws_apigatewayv2_api.notes_http.id
  name                              = "ztxp-pep"
  authorizer_type                   = "REQUEST"
  authorizer_uri                    = aws_lambda_function.pep.invoke_arn
  identity_sources                  = ["$request.header.Authorization"]
  authorizer_payload_format_version = "2.0"
}

###############################################
# INTEGRATION & ROUTE
###############################################

resource "aws_apigatewayv2_integration" "notes_lambda" {
  api_id                 = aws_apigatewayv2_api.notes_http.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.notes.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "notes_route" {
  api_id             = aws_apigatewayv2_api.notes_http.id
  route_key          = "ANY /notes/{proxy+}"
  target             = "integrations/${aws_apigatewayv2_integration.notes_lambda.id}"
  authorizer_id      = aws_apigatewayv2_authorizer.pep.id
  authorization_type = "CUSTOM"
}

###############################################
# PERMISSIONS
###############################################

resource "aws_lambda_permission" "pep_invoke" {
  statement_id  = "AllowAPIGwInvokePep"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.pep.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.notes_http.execution_arn}/*/*"
}

resource "aws_lambda_permission" "notes_invoke" {
  statement_id  = "AllowAPIGwInvokeNotes"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.notes.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.notes_http.execution_arn}/*/*"
}

###############################################
# OUTPUT
###############################################

output "api_url" {
  value = aws_apigatewayv2_api.notes_http.api_endpoint
}
