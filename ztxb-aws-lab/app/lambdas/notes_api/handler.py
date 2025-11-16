# app/lambdas/notes_api/handler.py
import json
import os
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TABLE_NAME = os.environ.get("TABLE_NAME", "unknown")

def lambda_handler(event, context):
    """
    Minimal stub Notes API.
    Later we can wire this up to DynamoDB for real CRUD.
    """
    logger.info("Received event: %s", json.dumps(event))

    method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
    path   = event.get("rawPath", "/notes")

    body = {
        "message": "Notes API stub",
        "method": method,
        "path": path,
        "table": TABLE_NAME,
    }

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }
