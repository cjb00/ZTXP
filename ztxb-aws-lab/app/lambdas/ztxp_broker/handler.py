# app/lambdas/ztxp_broker/handler.py
"""
ZTXP Broker — receives signed TAMs from the PEP, verifies the
signature via KMS, then forwards the TAM payload to the PDP
(Open Policy Agent) for a policy decision.

Security flow:
  1. Parse TAM from request body
  2. Verify ECDSA_SHA_256 signature against KMS public key
  3. Validate timestamp freshness (reject replay > 600 s)
  4. POST TAM fields to OPA at PDP_URL for policy evaluation
  5. Return the allow/deny decision
"""
import base64
import hashlib
import json
import logging
import os
from datetime import datetime, timezone, timedelta

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

PDP_URL = os.environ.get("PDP_URL", "")
KMS_KEY_ARN = os.environ.get("KMS_KEY_ARN", "")
TAM_TTL_SECONDS = int(os.environ.get("TAM_TTL_SECONDS", "600"))

kms_client = boto3.client("kms")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def canonical_json(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _error(status, message):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"decision": "deny", "reason": message}),
    }


# ---------------------------------------------------------------------------
# Signature verification
# ---------------------------------------------------------------------------

def verify_signature(tam):
    """Verify the TAM signature using KMS Verify (ECDSA_SHA_256).

    Returns True if valid, raises ValueError otherwise.
    """
    sig_block = tam.get("signature")
    if not sig_block:
        raise ValueError("missing_signature")

    sig_bytes = base64.b64decode(sig_block["sig"])

    # Reconstruct the canonical payload (everything except "signature")
    tam_copy = {k: v for k, v in tam.items() if k != "signature"}
    payload = canonical_json(tam_copy)
    digest = hashlib.sha256(payload).digest()

    key_id = sig_block.get("key_id", KMS_KEY_ARN)

    response = kms_client.verify(
        KeyId=key_id,
        Message=digest,
        MessageType="DIGEST",
        Signature=sig_bytes,
        SigningAlgorithm="ECDSA_SHA_256",
    )

    if not response.get("SignatureValid"):
        raise ValueError("invalid_signature")

    return True


def verify_timestamp(tam):
    """Reject TAMs whose issued_at is older than TAM_TTL_SECONDS."""
    issued_at_str = tam.get("issued_at", "")
    if not issued_at_str:
        raise ValueError("missing_timestamp")

    try:
        issued_at = datetime.strptime(issued_at_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        issued_at = datetime.fromisoformat(issued_at_str.replace("Z", "+00:00"))

    age = datetime.now(timezone.utc) - issued_at
    if age > timedelta(seconds=TAM_TTL_SECONDS):
        raise ValueError(f"tam_expired (age={int(age.total_seconds())}s, ttl={TAM_TTL_SECONDS}s)")
    if age < timedelta(seconds=-60):
        raise ValueError("tam_from_future")

    return True


# ---------------------------------------------------------------------------
# PDP call (OPA)
# ---------------------------------------------------------------------------

def call_pdp(tam):
    """Forward the TAM to OPA for policy evaluation.

    OPA expects:
      POST /v1/data/authz/allow
      { "input": { ... } }

    We map TAM fields to the OPA input schema that authz.rego expects.
    """
    from urllib.request import Request, urlopen
    from urllib.error import URLError

    opa_input = {
        "action": tam.get("resource", {}).get("action", ""),
        "principal": {
            "id": tam.get("subject", {}).get("id", ""),
            "role": tam.get("subject", {}).get("role", ""),
            "groups": tam.get("subject", {}).get("groups", []),
        },
        "resource": tam.get("resource", {}),
        "context": {
            "device_trust": tam.get("context", {}).get("device_trust", "unknown"),
            "risk_score": tam.get("context", {}).get("risk_score", 100),
            "compliant": tam.get("device", {}).get("posture", {}).get("compliant", False),
        },
    }

    url = f"http://{PDP_URL}/v1/data/authz/allow"
    body = json.dumps({"input": opa_input}).encode("utf-8")
    req = Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")

    try:
        with urlopen(req, timeout=3) as resp:
            result = json.loads(resp.read().decode())
            return result.get("result", False)
    except (URLError, Exception) as exc:
        logger.error("PDP call failed: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Lambda entry point
# ---------------------------------------------------------------------------

def lambda_handler(event, context):
    logger.info("Broker invoked")

    # Parse the TAM from the request body
    try:
        body = event.get("body", "")
        if isinstance(body, str):
            body = json.loads(body)
        tam = body.get("tam") if isinstance(body, dict) else None
        if not tam:
            return _error(400, "missing_tam")
    except (json.JSONDecodeError, AttributeError):
        return _error(400, "invalid_json")

    # 1. Verify signature
    try:
        verify_signature(tam)
    except ValueError as exc:
        logger.warning("Signature verification failed: %s", exc)
        return _error(403, f"signature_rejected: {exc}")
    except Exception as exc:
        logger.error("KMS verify error: %s", exc)
        return _error(500, "verification_error")

    # 2. Verify timestamp freshness (replay protection)
    try:
        verify_timestamp(tam)
    except ValueError as exc:
        logger.warning("Timestamp check failed: %s", exc)
        return _error(403, f"timestamp_rejected: {exc}")

    # 3. Forward to PDP for policy decision
    allowed = call_pdp(tam)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    decision = "allow" if allowed else "deny"
    reason = "policy_allow" if allowed else "policy_deny"

    logger.info("Decision for message_id=%s: %s", tam.get("message_id"), decision)

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({
            "decision": decision,
            "reason": reason,
            "evaluated_at": now,
            "expires_in": 300 if allowed else 0,
            "message_id": tam.get("message_id", ""),
        }),
    }
