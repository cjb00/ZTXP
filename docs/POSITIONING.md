# Why ZTXP? Positioning Zero Trust eXchange Protocol

## The Problem in One Sentence

When two Zero Trust systems need to exchange a trust decision — not just an identity token — there is no standard wire protocol to carry it.

---

## What Already Exists (And What It Doesn't Solve)

| Technology | What It Does Well | What It Doesn't Do |
|---|---|---|
| **SPIFFE/SPIRE** | Issues cryptographic workload identities (SVIDs) | Does not carry authorization context or trust reasoning |
| **OPA / Cedar** | Evaluates policy against input data | Does not define how trust context is packaged or transmitted between systems |
| **OpenID AuthZEN** | Standardizes the authorization API call | Scoped to a single PDP; no cross-domain trust propagation model |
| **IETF WIMSE** | Defines workload identity for multi-system environments | Addresses identity issuance, not trust assertion exchange |
| **OAuth 2.0 / JWT** | Carries claims across HTTP boundaries | General-purpose; no semantics for ZT trust posture, risk signals, or assertion chains |

None of these define how a verifiable trust assertion — including *why* a decision was made, not just *what* it was — travels between two independently-operated Zero Trust domains.

---

## What ZTXP Defines

ZTXP introduces the **Trust Assertion Message (TAM)**: a compact, cryptographically signed structure that encodes:

- **Subject** — the workload or identity being asserted about
- **Issuer** — the ZT control plane that made the assertion
- **Trust Level** — a normalized posture signal (e.g., `HIGH`, `CONDITIONAL`, `DENIED`)
- **Evidence** — the policy inputs that drove the decision (device posture, auth method, risk score)
- **Chain** — a tamper-evident chain of prior assertions when trust crosses multiple domains
- **Expiry** — short-lived by design; no stale trust propagation

ZTXP is **not** a policy engine. It does not replace OPA, Cedar, or any PDP. It is the **envelope** that lets a trust decision made by one ZT system be verifiably consumed by another.

ZTXP is **not** an identity protocol. It does not replace SPIFFE SVIDs or JWT. A TAM *references* an identity; it does not re-issue one.

---

## The Gap ZTXP Fills

Consider this scenario:

> A workload in Agency A's Zero Trust enclave needs to call a service in Agency B's enclave. Agency A's PDP has already evaluated the request and determined the workload is trusted at level `HIGH`. Agency B's PDP needs to consume that decision — but also needs to verify it wasn't tampered with, understand what evidence produced it, and apply its own policy on top.

Today, there is no standard way to do this. Organizations solve it with:
- Bilateral API integrations (brittle, vendor-specific)
- Re-authentication at every boundary (high latency, trust context loss)
- Out-of-band federation agreements (slow, not machine-readable)

ZTXP solves this with a single signed message that any conforming implementation can produce and verify.

---

## Relationship to Existing Standards

ZTXP is designed to **compose with**, not compete with, existing ZT infrastructure:

- **SPIFFE/SPIRE** issues the identity embedded in a TAM's `subject` field
- **OPA/Cedar** produces the policy decision that a TAM's `trust_level` and `evidence` fields encode
- **AuthZEN** may be the API through which a TAM is delivered to a remote PDP
- **WIMSE** provides the workload identity context ZTXP builds upon
- **TLS** secures the transport; ZTXP secures the **meaning** of what is exchanged

---

## Who Should Care

- **Platform engineers** building multi-cluster or multi-cloud ZT architectures who need cross-boundary trust propagation
- **IC / DoD integrators** dealing with cross-domain solution requirements where trust posture must be verifiable end-to-end
- **CNCF / SPIFFE ecosystem contributors** looking to close the gap between workload identity and authorization context portability
- **Standards participants** in IETF WIMSE, OpenID AuthZEN, and related working groups

---

## Current Status

- **Specification:** `draft-ztxp-02` (working draft, not yet submitted to IETF)
- **Reference Implementation:** Python toolkit for TAM signing, verification, and OPA-based evaluation
- **Lab Environment:** AWS HCL lab demonstrating ZTXB (Zero Trust eXchange Broker) deployment pattern
- **License:** Apache 2.0

The project is actively seeking:
- Review and feedback on the draft spec
- Second implementation contributors (Go or Rust preferred)
- Engagement from IETF WIMSE, CNCF TAG Security, and AuthZEN community members

---

## Get Involved

- **Spec:** [spec/draft-ztxp-02.md](../spec/draft-ztxp-02.md)
- **Reference impl:** [reference/ztxp-v0.2.py](../reference/ztxp-v0.2.py)
- **Discussions:** GitHub Discussions tab — open questions, design proposals
- **Contact:** Open an issue or start a Discussion thread

---

*ZTXP is an independent open protocol effort. It is not affiliated with any vendor, standards body, or government program.*
