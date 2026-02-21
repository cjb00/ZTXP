# tests/test_pep_authorizer.py
"""Unit tests for the PEP Authorizer Lambda handler."""
import base64
import importlib
import json
import sys
import os
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

import pytest

# Use importlib to avoid module name collisions between handler.py files
_pep_dir = os.path.join(os.path.dirname(__file__), "..", "app", "lambdas", "pep_authorizer")

with patch.dict(os.environ, {"KMS_KEY_ARN": "arn:aws:kms:us-east-1:123456789012:key/test-key", "BROKER_URL": "https://broker.example.com"}):
    with patch("boto3.client"):
        spec = importlib.util.spec_from_file_location("pep_handler", os.path.join(_pep_dir, "handler.py"))
        pep = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pep)


def _make_event(method="GET", path="/notes", auth_header="", extra_headers=None):
    headers = {"authorization": auth_header}
    if extra_headers:
        headers.update(extra_headers)
    return {
        "requestContext": {
            "http": {"method": method, "path": path, "sourceIp": "10.0.0.1"},
            "requestId": "test-req-123",
        },
        "headers": headers,
    }


class TestBuildTam:
    def test_basic_tam_structure(self):
        event = _make_event()
        tam = pep.build_tam(event)

        assert tam["version"] == "0.2"
        assert "message_id" in tam
        assert "issued_at" in tam
        assert tam["issuer"] == "ztxp://pep.ztxp-aws-lab"
        assert tam["subject"]["id"] == "user:anonymous"
        assert tam["resource"]["action"] == "notes:Read"

    def test_write_action_for_post(self):
        event = _make_event(method="POST")
        tam = pep.build_tam(event)
        assert tam["resource"]["action"] == "notes:Write"

    def test_write_action_for_put(self):
        event = _make_event(method="PUT")
        tam = pep.build_tam(event)
        assert tam["resource"]["action"] == "notes:Write"

    def test_write_action_for_delete(self):
        event = _make_event(method="DELETE")
        tam = pep.build_tam(event)
        assert tam["resource"]["action"] == "notes:Write"

    def test_read_action_for_get(self):
        event = _make_event(method="GET")
        tam = pep.build_tam(event)
        assert tam["resource"]["action"] == "notes:Read"

    def test_device_context_headers(self):
        event = _make_event(extra_headers={
            "x-device-id": "laptop-42",
            "x-device-compliant": "false",
            "x-device-trust": "high-risk",
        })
        tam = pep.build_tam(event)
        assert tam["device"]["id"] == "device:laptop-42"
        assert tam["device"]["posture"]["compliant"] is False
        assert tam["context"]["device_trust"] == "high-risk"

    def test_jwt_subject_extraction(self):
        claims = {"sub": "user-abc-123", "email": "test@example.com"}
        payload = base64.b64encode(json.dumps(claims).encode()).decode().rstrip("=")
        fake_jwt = f"eyJhbGciOiJSUzI1NiJ9.{payload}.fake-sig"

        event = _make_event(auth_header=f"Bearer {fake_jwt}")
        tam = pep.build_tam(event)
        assert tam["subject"]["id"] == "user:user-abc-123"

    def test_cognito_groups_extracted(self):
        claims = {"sub": "user-abc-123", "cognito:groups": ["writer", "admin"]}
        payload = base64.b64encode(json.dumps(claims).encode()).decode().rstrip("=")
        fake_jwt = f"eyJhbGciOiJSUzI1NiJ9.{payload}.fake-sig"

        event = _make_event(auth_header=f"Bearer {fake_jwt}")
        tam = pep.build_tam(event)
        assert tam["subject"]["groups"] == ["writer", "admin"]

    def test_no_groups_when_missing(self):
        claims = {"sub": "user-abc-123"}
        payload = base64.b64encode(json.dumps(claims).encode()).decode().rstrip("=")
        fake_jwt = f"eyJhbGciOiJSUzI1NiJ9.{payload}.fake-sig"

        event = _make_event(auth_header=f"Bearer {fake_jwt}")
        tam = pep.build_tam(event)
        assert tam["subject"]["groups"] == []


class TestDecodeJwtClaims:
    def test_decodes_claims(self):
        claims = {"sub": "abc", "cognito:groups": ["writer"]}
        payload = base64.b64encode(json.dumps(claims).encode()).decode().rstrip("=")
        fake_jwt = f"header.{payload}.sig"
        result = pep._decode_jwt_claims(f"Bearer {fake_jwt}")
        assert result["sub"] == "abc"
        assert result["cognito:groups"] == ["writer"]

    def test_returns_empty_on_bad_token(self):
        result = pep._decode_jwt_claims("Bearer not.valid")
        assert result == {}


class TestCanonicalJson:
    def test_deterministic(self):
        data = {"b": 2, "a": 1}
        result = pep.canonical_json(data)
        assert result == b'{"a":1,"b":2}'

    def test_no_whitespace(self):
        data = {"key": "value"}
        result = pep.canonical_json(data)
        assert b" " not in result


class TestLambdaHandler:
    @patch.object(pep, "call_broker")
    @patch.object(pep, "sign_tam")
    def test_allow_decision(self, mock_sign, mock_broker):
        mock_sign.side_effect = lambda tam: {**tam, "signature": {"alg": "test", "sig": "abc", "key_id": "k"}}
        mock_broker.return_value = {"decision": "allow", "reason": "policy_allow"}

        event = _make_event()
        result = pep.lambda_handler(event, None)

        assert result["isAuthorized"] is True
        assert result["context"]["ztxp_decision"] == "allow"

    @patch.object(pep, "call_broker")
    @patch.object(pep, "sign_tam")
    def test_deny_decision(self, mock_sign, mock_broker):
        mock_sign.side_effect = lambda tam: {**tam, "signature": {"alg": "test", "sig": "abc", "key_id": "k"}}
        mock_broker.return_value = {"decision": "deny", "reason": "policy_deny"}

        event = _make_event()
        result = pep.lambda_handler(event, None)

        assert result["isAuthorized"] is False
        assert result["context"]["ztxp_decision"] == "deny"

    @patch.object(pep, "sign_tam", side_effect=Exception("KMS error"))
    def test_signing_failure_denies(self, mock_sign):
        event = _make_event()
        result = pep.lambda_handler(event, None)

        assert result["isAuthorized"] is False
        assert result["context"]["reason"] == "signing_failed"
