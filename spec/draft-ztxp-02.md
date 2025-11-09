# draft-ztxp-02.md
## ZTXP: The Zero Trust eXchange Protocol (Version 0.2)

### Status of This Memo
This Internet-Draft is submitted for public review and comment.  
Distribution of this document is unlimited.  
Copyright © 2025 Clifford Bell. Licensed under the Apache 2.0 License.

---

## Abstract
The **Zero Trust eXchange Protocol (ZTXP)** defines a vendor-neutral, cryptographically verifiable format and API for conveying *trust context* between components in a Zero Trust Architecture (ZTA).  
Where TCP/IP moves packets and TLS secures the channel, **ZTXP carries the “why”** — the identity, device posture, environment, and risk data used to decide authorization.  
ZTXP introduces the **Trust Assertion Message (TAM)**: a signed JSON structure that can be evaluated locally or remotely through an AuthZEN-compatible API.

---

## 1. Introduction
Zero Trust systems depend on multiple, dynamic signals — identity, device, environment, and intent — to determine access. Each vendor expresses these differently.  
ZTXP defines a common envelope so that Policy Enforcement Points (PEPs), Brokers, and Policy Decision Points (PDPs) can exchange consistent, verifiable trust assertions independent of vendor or platform.

**Goals**
- Portable, machine-readable trust assertions  
- Lightweight cryptographic signing and verification  
- Compatibility with existing AuthZEN and OPA ecosystems  
- Extensibility for edge, cloud, and OT deployments  

---

## 2. Terminology

| Term | Meaning |
|------|----------|
| **TAM** | Trust Assertion Message — the signed JSON payload carrying trust context |
| **PEP** | Policy Enforcement Point — system collecting context and issuing a TAM |
| **PDP** | Policy Decision Point / Trust Broker — verifies and evaluates TAMs |
| **Trust Domain** | Boundary sharing key material and policy for verification |
| **OPA** | Open Policy Agent — external policy engine optionally integrated |

---

## 3. Protocol Overview
1. **Context Collection** — The PEP gathers identity, device posture, and risk metrics.  
2. **TAM Construction** — The data is serialized per the schema in §4 and signed with Ed25519.  
3. **Evaluation** — The PEP transmits the signed TAM to a PDP using HTTPS POST `/ztxp/evaluate`.  
4. **Decision** — The PDP verifies signature and timestamp, evaluates policy, and returns a decision JSON.

---

## 4. Trust Assertion Message (TAM) Schema
```json
{
  "version": "0.2",
  "issuer": "ztxp://broker.example.com",
  "issued_at": "2025-11-08T04:00:00Z",
  "subject": {
    "id": "user:alice@example.com",
    "role": "finance-analyst"
  },
  "device": {
    "id": "device:1234abcd",
    "posture": {
      "compliant": true,
      "os_version": "macOS 14.3",
      "attestation": "TPM2"
    }
  },
  "context": {
    "risk_score": 42,
    "geo": "US-TX",
    "session_id": "s-879293"
  },
  "resource": {
    "id": "app://internal-finance",
    "action": "read"
  },
  "signature": {
    "alg": "Ed25519",
    "key_id": "ztxp://keys/broker-key",
    "sig": "<base64-encoded-signature>"
  }
}
```
All fields are mandatory unless marked *optional* in a future extension. The entire canonical JSON (excluding `signature`) is signed.

---

## 5. Signing and Verification
- **Algorithm:** Ed25519 (default); Ed448 or ECDSA P-256 allowed by extension.  
- **Replay Protection:** Brokers reject TAMs older than the configured TTL (default 600 s).  
- **Key Distribution:** JWKS endpoint or static PEM; key URIs identified via `key_id`.  
- **Canonicalization:** UTF-8, sorted keys, no insignificant whitespace.  
- **Verification:** Canonical JSON (excluding `signature`) MUST verify against the declared algorithm and public key.  
- **Revocation:** Keys SHOULD support rotation and revocation lists distributed through `/ztxp/metadata`.

---

## 6. Evaluation API

### Request
```http
POST /ztxp/evaluate
Content-Type: application/json

{
  "tam": { ... signed TAM JSON ... }
}
```

### Response
```json
{
  "decision": "allow",
  "evaluated_at": "2025-11-08T04:02:00Z",
  "expires_in": 600,
  "reason": "device compliant, low risk"
}
```

This API is intentionally compatible with the **OpenID AuthZEN “evaluate”** interface, enabling direct interoperation with existing PDPs and authorization brokers.

---

## 7. Extensions

| Area | Description |
|------|--------------|
| **mTLS Binding** | Bind TAM issuance to the TLS session fingerprint for end-to-end integrity. |
| **OPA Hook** | Forward canonical TAM data to a local Rego policy bundle for fine-grained evaluation. |
| **Health & Metadata** | `/ztxp/health` and `/ztxp/metadata` expose broker status, keys, and versioning. |
| **Multi-Key Domains** | Domain descriptors supporting key rotation and chained trust anchors. |
| **Compact Encoding** | Optional CBOR or FlatBuffers representation for constrained / IoT links. |

---

## 8. Reference Implementation
The reference Python toolkit **`ztxp-v0.2.py`** includes:

- `sign` – generate signed TAMs from YAML or JSON  
- `verify` – validate signature and timestamp  
- `broker` – HTTP evaluation service  
- `opa` – optional Open Policy Agent integration  

**Repository:** [https://github.com/cliffbell/ZTXP](https://github.com/cliffbell/ZTXP)

**Example workflow**
```bash
python ztxp-v0.2.py sign tam.yaml signed.json
python ztxp-v0.2.py broker --port 8080
curl -X POST -H "Content-Type: application/json"      --data @signed.json      http://127.0.0.1:8080/ztxp/evaluate
```

---

## 9. Security Considerations
ZTXP messages are integrity-protected but not confidential. Implementations **MUST** transmit TAMs only over mutually authenticated TLS 1.3 (or equivalent).

**Guidelines**
- Compromise of a signing key invalidates prior assertions; keys **SHOULD** be versioned and rotated.  
- Time synchronization across trust domains is **REQUIRED** to prevent replay.  
- Brokers **SHOULD** enforce issuer allow-lists and per-domain policy constraints.  
- Implementations **SHOULD** log verification failures and rejected TAMs for auditing.

---

## 10. IANA Considerations
This document requests registration of the following media type:

| Field | Value |
|------|-------|
| **Name** | ZTXP (JSON) |
| **Type** | `application/ztxp+json` |
| **Extensions** | `.ztxp`, `.tam` |
| **Reference** | This document (draft-bell-ztxp-02) |

---

## 11. Acknowledgments
Thanks to contributors in the **AuthZEN Working Group**, the **Open Policy Agent community**, and Zero Trust Architecture researchers whose feedback shaped this specification. Special appreciation to early implementers who validated TAM signing and broker interoperability across edge and cloud systems.

---

## 12. References
- **NIST SP 800-207** – *Zero Trust Architecture*  
- **CISA** – *Zero Trust Maturity Model v2.0*  
- **OpenID Foundation AuthZEN Working Group** – Draft Specifications (2024–2025)  
- **Open Policy Agent (OPA)** – Rego Policy Language and Project Documentation  
- **IETF RFC 7519** – JSON Web Token (JWT) for claim encoding reference  

---

## Author’s Address
**Clifford Bell**  
Email: [cjb2@proton.me](mailto:cjb2@proton.me)  
GitHub: https://github.com/cliffbell

---
