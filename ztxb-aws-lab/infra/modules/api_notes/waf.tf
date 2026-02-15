###############################################
# WAF v2 — rate limiting + AWS managed rules
###############################################

resource "aws_wafv2_web_acl" "notes" {
  name        = "${var.project}-notes-waf"
  scope       = "REGIONAL"
  description = "WAF for Notes API"

  default_action {
    allow {}
  }

  # Rate limit: 500 requests per 5 minutes per IP
  rule {
    name     = "rate-limit"
    priority = 1

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit              = 500
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      sampled_requests_enabled   = true
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.project}-rate-limit"
    }
  }

  # AWS Managed — common attack patterns (SQLi, XSS, etc.)
  rule {
    name     = "aws-common-rules"
    priority = 2

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name        = "AWSManagedRulesCommonRuleSet"
      }
    }

    visibility_config {
      sampled_requests_enabled   = true
      cloudwatch_metrics_enabled = true
      metric_name                = "${var.project}-common-rules"
    }
  }

  visibility_config {
    sampled_requests_enabled   = true
    cloudwatch_metrics_enabled = true
    metric_name                = "${var.project}-notes-waf"
  }
}

resource "aws_wafv2_web_acl_association" "notes" {
  resource_arn = aws_apigatewayv2_stage.notes_default.arn
  web_acl_arn  = aws_wafv2_web_acl.notes.arn
}
