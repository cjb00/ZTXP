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

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in BCP 14 [RFC 2119] [RFC 8174] when, and only when, they appear in all capitals, as shown here.

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
The reference Python toolkit **`ztxpv0.2.py`** includes:

- `sign` – generate signed TAMs from YAML or JSON
- `verify` – validate signature and timestamp
- `broker` – HTTP evaluation service
- `opa` – optional Open Policy Agent integration

**Repository:** [https://github.com/cjb00/ZTXP](https://github.com/cjb00/ZTXP)

**Example workflow**
```bash
python ztxpv0.2.py sign tam.yaml signed.json
python ztxpv0.2.py broker --port 8080
curl -X POST -H "Content-Type: application/json" \
     --data @signed.json \
     http://127.0.0.1:8080/ztxp/evaluate
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

## 10. Conformance Requirements

This section specifies normative requirements for conforming ZTXP implementations. The keywords used here are as defined in §2.

### 10.1 TAM Structure Requirements

A conforming implementation MUST validate that a received TAM contains all required top-level fields before processing. The following fields are REQUIRED (see §4 for schema details):

- `version` — MUST be a non-empty string. Unknown version values SHOULD cause the TAM to be rejected.
- `issuer` — MUST be a valid URI.
- `issued_at` — MUST be present and parseable as an RFC 3339 timestamp.
- `subject` — MUST be present and MUST contain an `id` field. The `role` field is OPTIONAL.
- `device` — MUST be present and MUST contain an `id` field. The `posture` sub-object is OPTIONAL.
- `context` — MUST be present. If `risk_score` is present, it MUST be an integer in the range [0, 100].
- `resource` — MUST be present and MUST contain both an `id` field and an `action` field.
- `signature` — MUST be present and MUST contain `alg`, `key_id`, and `sig` fields.

A conforming implementation MUST NOT reject a TAM solely because it contains unrecognized top-level fields. Unknown fields SHOULD be preserved and passed through to the policy evaluator.

### 10.2 Signing and Verification Requirements

Conforming implementations MUST support Ed25519 as the baseline signing algorithm (see §5). Ed448 and ECDSA P-256 MAY be supported as additional algorithms.

- Implementations MUST NOT accept a TAM whose `signature.alg` value is unrecognized, unless the implementation is explicitly configured to accept it.
- The canonical form used for signing and verification MUST be UTF-8 encoded, with JSON keys sorted lexicographically and no insignificant whitespace, with the `signature` object excluded from the input bytes.
- A verifying implementation MUST reconstruct the canonical form from the received JSON before verifying the signature. It MUST NOT verify against raw received bytes.
- Implementations MUST NOT accept a TAM whose cryptographic signature fails verification.
- Key distribution MUST be supported via JWKS endpoint or static PEM file, identified through the `key_id` URI.

### 10.3 Trust Level Normalization

Implementations MUST interpret trust signal fields consistently:

- `context.risk_score`, when present, MUST be treated as an integer in [0, 100], where 0 represents the lowest risk and 100 represents the highest. A value outside this range MUST cause the TAM to be rejected; implementations MUST NOT silently clamp or normalize out-of-range values.
- `device.posture.compliant`, when present, MUST be a boolean. A value of `false` SHOULD result in a deny decision unless the governing policy explicitly permits non-compliant devices.
- Implementations MUST log the reason when a TAM is rejected due to invalid trust signal values.

### 10.4 Evidence Field Handling

The `device.posture.attestation` field, when present, represents an evidence claim about device integrity (see §4).

- A conforming implementation MUST NOT treat an attestation claim as independently verified without an out-of-band verification path (e.g., TPM quote verification, MDM policy check, or hardware attestation API).
- Implementations MUST NOT forward an unverified attestation claim to downstream consumers as if it were verified.
- Implementations SHOULD log the attestation scheme value and the outcome of any verification attempt.
- An unrecognized attestation scheme value SHOULD be treated as unverified evidence. Implementations MUST NOT reject a TAM solely because the attestation scheme is unrecognized.

### 10.5 Chain of Custody Requirements

When a TAM is forwarded across trust domain boundaries (see §7, Multi-Key Domains):

- The forwarding entity MUST NOT remove, alter, or overwrite any `signature` object from a prior trust domain.
- If a forwarding entity appends its own assertion, it MUST add a new signature block using the agreed multi-signature structure and MUST NOT replace the originating signature.
- A consuming PDP MUST verify each signature in the chain against the key material of the corresponding trust domain.
- Implementations MUST NOT accept a TAM presented as cross-domain if any signature in the custody chain fails verification.

### 10.6 Expiry Enforcement

Conforming consumers MUST enforce TAM lifetime as follows (see §5 for TTL defaults):

- A TAM MUST be rejected if its `issued_at` timestamp plus the applicable TTL precedes the current evaluation time.
- The default TTL is 600 seconds. A PDP MAY enforce a stricter TTL; it MUST NOT honor a TTL longer than the value advertised in its `/ztxp/metadata` response.
- A TAM with an `issued_at` value more than the permitted clock skew in the future MUST be rejected. The RECOMMENDED maximum clock skew is 30 seconds.
- Implementations MUST NOT cache an evaluation decision beyond the duration expressed in the response `expires_in` field (see §6).

### 10.7 Interoperability Requirements

A conforming ZTXP implementation that exposes an evaluation service MUST satisfy the following (see §6):

- Accept `POST /ztxp/evaluate` with `Content-Type: application/json` and a request body containing a `tam` field.
- Return a JSON response containing at minimum: `decision` (one of `"allow"` or `"deny"`), `evaluated_at` (RFC 3339 timestamp), and `expires_in` (non-negative integer, seconds).
- Return HTTP 400 for requests with structurally invalid TAMs.
- Return HTTP 403 for valid TAMs that result in a deny decision.
- Expose `GET /ztxp/metadata` returning at minimum: the list of supported `alg` values, active `key_id` identifiers, and the implementation's `version` string.

A conforming implementation MAY expose `GET /ztxp/health`.

Implementations MUST NOT require proprietary extensions to the TAM structure or evaluation API in order to produce a basic allow or deny decision.

---

## 11. IANA Considerations
This document requests registration of the following media type:

| Field | Value |
|------|-------|
| **Name** | ZTXP (JSON) |
| **Type** | `application/ztxp+json` |
| **Extensions** | `.ztxp`, `.tam` |
| **Reference** | This document (draft-bell-ztxp-02) |

---

## 12. Acknowledgments
Thanks to contributors in the **AuthZEN Working Group**, the **Open Policy Agent community**, and Zero Trust Architecture researchers whose feedback shaped this specification. Special appreciation to early implementers who validated TAM signing and broker interoperability across edge and cloud systems.

---

## 13. References
- **IETF RFC 2119** – *Key words for use in RFCs to Indicate Requirement Levels*, Bradner, S. (1997)  
- **IETF RFC 8174** – *Ambiguity of Uppercase vs Lowercase in RFC 2119 Key Words*, Leiba, B. (2017)  
- **IETF RFC 7519** – JSON Web Token (JWT) for claim encoding reference  
- **NIST SP 800-207** – *Zero Trust Architecture*  
- **CISA** – *Zero Trust Maturity Model v2.0*  
- **OpenID Foundation AuthZEN Working Group** – Draft Specifications (2024–2025)  
- **Open Policy Agent (OPA)** – Rego Policy Language and Project Documentation  

---

## Author’s Address
**Clifford Bell**  
Email: [cjb2@proton.me](mailto:cjb2@proton.me)  
GitHub: https://github.com/cjb00

---
