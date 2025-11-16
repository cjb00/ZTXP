# app/lambdas/pep_authorizer/handler.py
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Minimal PEP stub for HTTP API v2 REQUEST authorizer.
    For now: allow every request.
    Later: build ZTXP TAM, sign with KMS, call broker.
    """
    logger.info("Authorizer event: %s", json.dumps(event))

    # You can extract identity info here for future use
    identity = event.get("identity", {}) or {}
    principal_id = identity.get("user", "anonymous")

    # HTTP API v2 request authorizer response shape
    return {
        "isAuthorized": True,
        "context": {
            "principalId": principal_id,
            "ztxp_decision": "allow_stub"
        }
    }
