```mermaid
flowchart LR
    A[User / Device] -->|Context & Posture| B[PEP]
    B -->|Builds signed TAM| C[ZTXP Broker]
    C -->|Verify signature<br/>Evaluate policy| D[PDP / Policy Engine]
    D -->|Decision: allow/deny<br/>TTL + reason| B
    D --> E[Audit / Log]
