# app/lambdas/pep_authorizer/handler.py
"""
PEP (Policy Enforcement Point) — HTTP API v2 REQUEST authorizer.

Collects identity and device context from the incoming request,
constructs a ZTXP Trust Assertion Message (TAM), signs it with
AWS KMS (ECDSA_SHA_256 / P-256), and forwards it to the ZTXP
Broker for a policy decision.

If the Broker says "allow", the request proceeds to the Notes API.
Otherwise the request is denied at the gateway.
"""
import base64
import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timezone

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

KMS_KEY_ARN = os.environ.get("KMS_KEY_ARN", "")
BROKER_URL = os.environ.get("BROKER_URL", "")

kms_client = boto3.client("kms")

# ---------------------------------------------------------------------------
# TAM helpers
# ---------------------------------------------------------------------------

def canonical_json(data):
    """Deterministic JSON serialisation for signing (sorted keys, no whitespace)."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def build_tam(event):
    """Extract identity / device / resource context from the API Gateway event
    and assemble a TAM according to the ZTXP v0.2 spec."""

    request_context = event.get("requestContext", {})
    http_info = request_context.get("http", {})
    headers = event.get("headers", {})

    # --- Identity (from Cognito JWT or Authorization header) ---
    auth_header = headers.get("authorization", "")
    principal_id = "anonymous"
    groups = []
    if auth_header:
        principal_id = _extract_sub_from_jwt(auth_header) or auth_header[:40]

    # --- Device context (forwarded by client headers) ---
    device_id = headers.get("x-device-id", "unknown")
    device_compliant = headers.get("x-device-compliant", "true").lower() == "true"
    device_trust = headers.get("x-device-trust", "low-risk")

    # --- Resource ---
    method = http_info.get("method", "GET")
    path = http_info.get("path", "/")
    action = "notes:Write" if method in ("POST", "PUT", "DELETE") else "notes:Read"

    tam = {
        "version": "0.2",
        "message_id": str(uuid.uuid4()),
        "issued_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "issuer": "ztxp://pep.ztxp-aws-lab",
        "subject": {
            "id": f"user:{principal_id}",
            "role": "authenticated",
            "groups": groups,
        },
        "device": {
            "id": f"device:{device_id}",
            "posture": {
                "compliant": device_compliant,
            },
        },
        "context": {
            "risk_score": 0,
            "device_trust": device_trust,
            "source_ip": http_info.get("sourceIp", "0.0.0.0"),
            "session_id": request_context.get("requestId", ""),
        },
        "resource": {
            "id": f"app://notes{path}",
            "action": action,
        },
    }
    return tam


def sign_tam(tam):
    """Sign the TAM with KMS (ECDSA_SHA_256 on P-256 key).

    KMS Sign with ECDSA_SHA_256 and MessageType=DIGEST expects us
    to SHA-256 the canonical payload ourselves.
    """
    payload = canonical_json(tam)
    digest = hashlib.sha256(payload).digest()

    response = kms_client.sign(
        KeyId=KMS_KEY_ARN,
        Message=digest,
        MessageType="DIGEST",
        SigningAlgorithm="ECDSA_SHA_256",
    )
    sig_bytes = response["Signature"]
    tam["signature"] = {
        "alg": "ECDSA_SHA_256",
        "key_id": KMS_KEY_ARN,
        "sig": base64.b64encode(sig_bytes).decode(),
    }
    return tam


# ---------------------------------------------------------------------------
# Broker call
# ---------------------------------------------------------------------------

def call_broker(signed_tam):
    """POST the signed TAM to the ZTXP Broker and return its decision."""
    from urllib.request import Request, urlopen
    from urllib.error import URLError

    url = f"{BROKER_URL}/ztxp/evaluate"
    body = json.dumps({"tam": signed_tam}).encode("utf-8")
    req = Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")

    try:
        with urlopen(req, timeout=4) as resp:
            return json.loads(resp.read().decode())
    except (URLError, Exception) as exc:
        logger.error("Broker call failed: %s", exc)
        return {"decision": "deny", "reason": "broker_unreachable"}


# ---------------------------------------------------------------------------
# JWT helper (lightweight — no external deps)
# ---------------------------------------------------------------------------

def _extract_sub_from_jwt(auth_header):
    """Best-effort extraction of 'sub' claim from a Bearer JWT.
    We do NOT verify the JWT here — Cognito + API Gateway handle that.
    We only need the subject identifier for the TAM."""
    try:
        token = auth_header.replace("Bearer ", "").strip()
        payload_segment = token.split(".")[1]
        padding = 4 - len(payload_segment) % 4
        payload_segment += "=" * padding
        claims = json.loads(base64.b64decode(payload_segment))
        return claims.get("sub") or claims.get("email") or claims.get("cognito:username")
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Lambda entry point
# ---------------------------------------------------------------------------

def lambda_handler(event, context):
    logger.info("PEP authorizer invoked")

    # 1. Build the TAM from request context
    tam = build_tam(event)

    # 2. Sign with KMS
    try:
        signed_tam = sign_tam(tam)
    except Exception as exc:
        logger.error("KMS signing failed: %s", exc)
        return {"isAuthorized": False, "context": {"reason": "signing_failed"}}

    # 3. Forward to the Broker for a policy decision
    decision = call_broker(signed_tam)
    logger.info("Broker decision: %s", json.dumps(decision))

    allowed = decision.get("decision") == "allow"

    # 4. Return authorizer response to API Gateway
    return {
        "isAuthorized": allowed,
        "context": {
            "principalId": tam["subject"]["id"],
            "ztxp_decision": decision.get("decision", "deny"),
            "ztxp_reason": decision.get("reason", ""),
            "ztxp_message_id": tam["message_id"],
        },
    }
