"""
ZTXP Toolkit (v0.2 prototype)
===========================
A minimal Python reference implementation for:
  1. Trust Assertion Message (TAM) creation, signing, and validation
  2. An HTTP Trust Broker that evaluates signed TAMs against simple policy
  3. A CLI for developer testing

Dependencies (install via pip):
  cryptography>=42.0.0
  flask>=3.0.0
  pyyaml>=6.0.0

Example usage:
  # Generate a keypair (if not present) and sign a TAM
  python ztxp_toolkit.py sign tam.yaml signed_tam.json

  # Validate a signed TAM
  python ztxp_toolkit.py validate signed_tam.json

  # Run broker on localhost:8080
  python ztxp_toolkit.py broker --host 0.0.0.0 --port 8080

  # In another terminal, post the signed TAM
  curl -X POST -H "Content-Type: application/json" \
       --data @signed_tam.json http://localhost:8080/ztxp/evaluate

Security Notes:
  • Ed25519 is used for compact, high-performance signatures.
  • Messages are canonicalized (sorted keys, UTF-8) prior to signing.
  • Basic replay protection via message_id (UUID) and timestamp checks.
  • Policy logic is intentionally simple: adjust in `evaluate_policy()`.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict

import yaml
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature

# ---------------------------
# Key Management Helpers
# ---------------------------
KEY_DIR = Path.home() / ".ztxp"
PRIV_KEY_PATH = KEY_DIR / "ed25519_private_key.pem"
PUB_KEY_PATH = KEY_DIR / "ed25519_public_key.pem"


def generate_keypair() -> None:
    KEY_DIR.mkdir(parents=True, exist_ok=True)
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    with open(PRIV_KEY_PATH, "wb") as f:
        f.write(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

    with open(PUB_KEY_PATH, "wb") as f:
        f.write(
            public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )
    print(f"[*] New Ed25519 keypair generated in {KEY_DIR}")


def load_private_key():
    if not PRIV_KEY_PATH.exists():
        generate_keypair()
    with open(PRIV_KEY_PATH, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def load_public_key():
    if not PUB_KEY_PATH.exists():
        raise FileNotFoundError("Public key not found; generate keypair first.")
    with open(PUB_KEY_PATH, "rb") as f:
        return serialization.load_pem_public_key(f.read())


# ---------------------------
# Trust Message Helpers
# ---------------------------
REQUIRED_TOP_LEVEL_FIELDS = {
    "ztxp_version",
    "message_id",
    "timestamp",
    "subject",
    "source_device",
    "resource",
    "context",
    "signature",
}


def canonical_json(data: Dict[str, Any]) -> bytes:
    """Deterministically serialize dict -> bytes for signing."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def validate_structure(msg: Dict[str, Any]) -> None:
    missing = REQUIRED_TOP_LEVEL_FIELDS - msg.keys()
    if missing:
        raise ValueError(f"Missing required top-level fields: {', '.join(sorted(missing))}")

    # Basic timestamp freshness check (±5 minutes)
    ts = datetime.fromisoformat(msg["timestamp"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    if abs(now - ts) > timedelta(minutes=5):
        raise ValueError("Timestamp is too far from current time (±5 min)")


def sign_message(tam: Dict[str, Any]) -> Dict[str, Any]:
    tam = tam.copy()
    priv_key = load_private_key()

    tam.setdefault("ztxp_version", "0.1")
    tam.setdefault("message_id", str(uuid.uuid4()))
    tam.setdefault("timestamp", datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))

    # Remove existing signature if present
    tam.pop("signature", None)

    payload = canonical_json(tam)
    signature = priv_key.sign(payload)
    sig_b64 = base64.b64encode(signature).decode()

    tam["signature"] = {
        "alg": "EdDSA",
        "key_id": PUB_KEY_PATH.stem,  # simplistic key_id
        "sig": sig_b64,
    }
    return tam


def verify_message(tam: Dict[str, Any]) -> bool:
    validate_structure(tam)
    sig_block = tam.pop("signature")
    try:
        pub_key = load_public_key()
        sig_bytes = base64.b64decode(sig_block["sig"])
        pub_key.verify(sig_bytes, canonical_json(tam))
    except (InvalidSignature, KeyError, ValueError) as e:
        raise ValueError(f"Signature verification failed: {e}")
    finally:
        tam["signature"] = sig_block  # restore
    return True


# ---------------------------
# Broker Implementation
# ---------------------------

def evaluate_policy(tam: Dict[str, Any]) -> Dict[str, Any]:
    """Simple policy engine for demo."""
    risk = tam["context"].get("risk_score", 100)
    compliant = tam["source_device"].get("posture", {}).get("compliant", False)
    decision = "allow" if risk < 50 and compliant else "deny"
    reason = []
    if risk >= 50:
        reason.append("high risk")
    if not compliant:
        reason.append("non-compliant device")

    return {
        "decision": decision,
        "reason": ", ".join(reason) or "low risk and compliant",
        "evaluated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "expires_in": 600 if decision == "allow" else 0,
    }


def run_broker(host: str, port: int):
    from flask import Flask, jsonify, request

    app = Flask(__name__)

    @app.route("/ztxp/evaluate", methods=["POST"])
    def evaluate():
        try:
            tam = request.get_json(force=True)
            verify_message(tam)
            decision = evaluate_policy(tam)
            return jsonify(decision)
        except Exception as e:
            return jsonify({"error": str(e)}), 400

    print(f"[*] ZTXP Broker listening on http://{host}:{port}")
    app.run(host=host, port=port, threaded=True)


# ---------------------------
# CLI Interface
# ---------------------------

def cli():
    parser = argparse.ArgumentParser(description="ZTXP Toolkit CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    # sign
    s = sub.add_parser("sign", help="Sign a TAM (YAML/JSON) -> JSON with signature")
    s.add_argument("input", help="Path to TAM YAML/JSON file")
    s.add_argument("output", help="Path to output signed JSON file")

    # validate
    v = sub.add_parser("validate", help="Validate a signed TAM JSON file")
    v.add_argument("input", help="Path to signed TAM JSON file")

    # broker
    b = sub.add_parser("broker", help="Run the Trust Broker API server")
    b.add_argument("--host", default="127.0.0.1", help="Bind address (default 127.0.0.1)")
    b.add_argument("--port", default=8080, type=int, help="Port (default 8080)")

    args = parser.parse_args()

    if args.command == "sign":
        with open(args.input, "r", encoding="utf-8") as f:
            if args.input.endswith((".yaml", ".yml")):
                tam_raw = yaml.safe_load(f)
            else:
                tam_raw = json.load(f)

        # --- actually sign & save ---------------------------------
        signed = sign_message(tam_raw)
        with open(args.output, "w", encoding="utf-8") as out:
            json.dump(signed, out, indent=2)
        print(f"[*] Signed TAM written to {args.output}")

    elif args.command == "validate":
        with open(args.input, "r", encoding="utf-8") as f:
            tam_raw = json.load(f)
        try:
            verify_message(tam_raw)
            print("[✓] Signature and structure valid")
        except Exception as e:
            print(f"[✗] Validation failed: {e}")
            sys.exit(1)

    elif args.command == "broker":
        run_broker(args.host, args.port)


if __name__ == "__main__":
    cli()