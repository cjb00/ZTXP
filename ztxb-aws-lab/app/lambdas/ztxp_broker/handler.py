# app/lambdas/ztxp_broker/handler.py
import json
import logging
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

PDP_URL = os.environ.get("PDP_URL", "http://pdp-placeholder")

def lambda_handler(event, context):
    """
    Minimal ZTXP broker stub.
    For now: log the TAM and return an 'allow' decision.
    Later: forward to PDP_URL and return real PDP decision.
    """
    logger.info("Broker event: %s", json.dumps(event))

    # In the real flow, event["body"] would be the signed TAM JSON.
    # For now just echo it and pretend PDP said allow.

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({
            "decision": "allow",
            "reason": "broker_stub",
            "evaluated_at": "stub",
            "expires_in": 300,
        }),
    }
