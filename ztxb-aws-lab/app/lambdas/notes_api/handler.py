# app/lambdas/notes_api/handler.py
"""
Notes API — a simple CRUD service backed by DynamoDB.

Only reachable after the PEP authorizer grants access. The
authorizer injects context (principalId, ztxp_decision) which
this handler uses to scope queries to the authenticated user.
"""
import json
import os
import logging
import uuid
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Key

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TABLE_NAME = os.environ.get("TABLE_NAME", "unknown")
ddb = boto3.resource("dynamodb")
table = ddb.Table(TABLE_NAME)


def _response(status, body):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def _user_id(event):
    """Extract the authenticated user from the authorizer context."""
    auth_ctx = event.get("requestContext", {}).get("authorizer", {}).get("lambda", {})
    return auth_ctx.get("principalId", "anonymous")


def _note_id_from_path(event):
    """Extract note_id from path parameters (/notes/{note_id})."""
    params = event.get("pathParameters") or {}
    proxy = params.get("proxy", "")
    return proxy.strip("/") if proxy else None


# ---------------------------------------------------------------------------
# CRUD operations
# ---------------------------------------------------------------------------

def list_notes(user_id):
    resp = table.query(KeyConditionExpression=Key("user_id").eq(user_id))
    return _response(200, {"notes": resp.get("Items", [])})


def get_note(user_id, note_id):
    resp = table.get_item(Key={"user_id": user_id, "note_id": note_id})
    item = resp.get("Item")
    if not item:
        return _response(404, {"error": "not_found"})
    return _response(200, item)


def create_note(user_id, body):
    note_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    item = {
        "user_id": user_id,
        "note_id": note_id,
        "title": body.get("title", ""),
        "content": body.get("content", ""),
        "created_at": now,
        "updated_at": now,
    }
    table.put_item(Item=item)
    return _response(201, item)


def update_note(user_id, note_id, body):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    resp = table.update_item(
        Key={"user_id": user_id, "note_id": note_id},
        UpdateExpression="SET title = :t, content = :c, updated_at = :u",
        ExpressionAttributeValues={
            ":t": body.get("title", ""),
            ":c": body.get("content", ""),
            ":u": now,
        },
        ConditionExpression="attribute_exists(user_id)",
        ReturnValues="ALL_NEW",
    )
    return _response(200, resp.get("Attributes", {}))


def delete_note(user_id, note_id):
    table.delete_item(
        Key={"user_id": user_id, "note_id": note_id},
        ConditionExpression="attribute_exists(user_id)",
    )
    return _response(200, {"deleted": note_id})


# ---------------------------------------------------------------------------
# Lambda entry point
# ---------------------------------------------------------------------------

def lambda_handler(event, context):
    logger.info("Notes API invoked")

    method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
    user_id = _user_id(event)
    note_id = _note_id_from_path(event)

    try:
        body = json.loads(event.get("body") or "{}") if event.get("body") else {}
    except json.JSONDecodeError:
        return _response(400, {"error": "invalid_json"})

    try:
        if method == "GET" and not note_id:
            return list_notes(user_id)
        elif method == "GET" and note_id:
            return get_note(user_id, note_id)
        elif method == "POST":
            return create_note(user_id, body)
        elif method == "PUT" and note_id:
            return update_note(user_id, note_id, body)
        elif method == "DELETE" and note_id:
            return delete_note(user_id, note_id)
        else:
            return _response(405, {"error": "method_not_allowed"})
    except Exception as exc:
        logger.error("Notes API error: %s", exc, exc_info=True)
        return _response(500, {"error": "internal_error"})
