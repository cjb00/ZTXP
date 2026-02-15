# app/pdp/policy/authz.rego
#
# ZTXP authorization policy for the Notes API.
#
# Input schema (mapped from TAM by the Broker):
#   input.action          - "notes:Read" | "notes:Write"
#   input.principal.id    - "user:<sub>"
#   input.principal.role  - e.g. "authenticated"
#   input.principal.groups - ["writer", "admin", ...]
#   input.context.device_trust  - "low-risk" | "medium-risk" | "high-risk"
#   input.context.risk_score    - integer 0-100
#   input.context.compliant     - boolean
#   input.resource.id     - "app://notes/..."
#   input.resource.action - same as input.action

package authz

import rego.v1

# Default deny — every request is blocked unless an allow rule fires
default allow := false

# -----------------------------------------------------------------------
# Read access: anyone with a non-high-risk device can read
# -----------------------------------------------------------------------
allow if {
    input.action == "notes:Read"
    not high_risk_device
}

# -----------------------------------------------------------------------
# Write access: must be in the "writer" group, device compliant and
# not flagged high-risk, and risk score below threshold
# -----------------------------------------------------------------------
allow if {
    input.action == "notes:Write"
    user_in_group("writer")
    input.context.compliant == true
    not high_risk_device
    input.context.risk_score < 70
}

# -----------------------------------------------------------------------
# Admin override: admins can do anything from compliant devices
# -----------------------------------------------------------------------
allow if {
    user_in_group("admin")
    input.context.compliant == true
    not high_risk_device
}

# -----------------------------------------------------------------------
# Helper rules
# -----------------------------------------------------------------------
user_in_group(g) if {
    some group in input.principal.groups
    group == g
}

high_risk_device if {
    input.context.device_trust == "high-risk"
}
