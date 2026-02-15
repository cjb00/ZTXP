# tests/test_broker.py
"""Unit tests for the ZTXP Broker Lambda handler."""
import importlib
import importlib.util
import json
import os
from unittest.mock import patch
from datetime import datetime, timezone, timedelta

import pytest

_broker_dir = os.path.join(os.path.dirname(__file__), "..", "app", "lambdas", "ztxp_broker")

with patch.dict(os.environ, {"PDP_URL": "pdp.internal", "KMS_KEY_ARN": "arn:aws:kms:us-east-1:123456789012:key/test-key"}):
    with patch("boto3.client"):
        spec = importlib.util.spec_from_file_location("broker_handler", os.path.join(_broker_dir, "handler.py"))
        broker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(broker)


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _make_tam(issued_at=None, signature=True):
    tam = {
        "version": "0.2",
        "message_id": "test-msg-001",
        "issued_at": issued_at or _now_iso(),
        "issuer": "ztxp://pep.test",
        "subject": {"id": "user:alice", "role": "authenticated", "groups": ["writer"]},
        "device": {"id": "device:abc", "posture": {"compliant": True}},
        "context": {"risk_score": 20, "device_trust": "low-risk"},
        "resource": {"id": "app://notes", "action": "notes:Read"},
    }
    if signature:
        tam["signature"] = {"alg": "ECDSA_SHA_256", "key_id": "arn:aws:kms:test", "sig": "dGVzdA=="}
    return tam


def _apigw_event(body):
    return {"body": json.dumps(body)}


class TestVerifyTimestamp:
    def test_fresh_timestamp(self):
        tam = _make_tam(signature=False)
        assert broker.verify_timestamp(tam) is True

    def test_expired_timestamp(self):
        old = (datetime.now(timezone.utc) - timedelta(seconds=700)).strftime("%Y-%m-%dT%H:%M:%SZ")
        tam = _make_tam(issued_at=old, signature=False)
        with pytest.raises(ValueError, match="tam_expired"):
            broker.verify_timestamp(tam)

    def test_future_timestamp(self):
        future = (datetime.now(timezone.utc) + timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
        tam = _make_tam(issued_at=future, signature=False)
        with pytest.raises(ValueError, match="tam_from_future"):
            broker.verify_timestamp(tam)

    def test_missing_timestamp(self):
        tam = _make_tam(signature=False)
        tam.pop("issued_at")
        with pytest.raises(ValueError, match="missing_timestamp"):
            broker.verify_timestamp(tam)


class TestCanonicalJson:
    def test_sorted_keys(self):
        result = broker.canonical_json({"z": 1, "a": 2})
        assert result == b'{"a":2,"z":1}'


class TestLambdaHandler:
    @patch.object(broker, "call_pdp", return_value=True)
    @patch.object(broker, "verify_signature")
    def test_allow_flow(self, mock_verify, mock_pdp):
        event = _apigw_event({"tam": _make_tam()})
        result = broker.lambda_handler(event, None)
        body = json.loads(result["body"])

        assert result["statusCode"] == 200
        assert body["decision"] == "allow"
        mock_verify.assert_called_once()
        mock_pdp.assert_called_once()

    @patch.object(broker, "call_pdp", return_value=False)
    @patch.object(broker, "verify_signature")
    def test_deny_flow(self, mock_verify, mock_pdp):
        event = _apigw_event({"tam": _make_tam()})
        result = broker.lambda_handler(event, None)
        body = json.loads(result["body"])

        assert body["decision"] == "deny"
        assert body["reason"] == "policy_deny"

    def test_missing_tam(self):
        event = _apigw_event({"not_tam": {}})
        result = broker.lambda_handler(event, None)
        assert result["statusCode"] == 400

    def test_invalid_json(self):
        event = {"body": "not json"}
        result = broker.lambda_handler(event, None)
        assert result["statusCode"] == 400

    @patch.object(broker, "verify_signature", side_effect=ValueError("invalid_signature"))
    def test_bad_signature(self, mock_verify):
        event = _apigw_event({"tam": _make_tam()})
        result = broker.lambda_handler(event, None)
        assert result["statusCode"] == 403
        assert "signature_rejected" in json.loads(result["body"])["reason"]

    @patch.object(broker, "verify_signature")
    def test_expired_tam(self, mock_verify):
        old = (datetime.now(timezone.utc) - timedelta(seconds=700)).strftime("%Y-%m-%dT%H:%M:%SZ")
        event = _apigw_event({"tam": _make_tam(issued_at=old)})
        result = broker.lambda_handler(event, None)
        assert result["statusCode"] == 403
        assert "timestamp_rejected" in json.loads(result["body"])["reason"]
