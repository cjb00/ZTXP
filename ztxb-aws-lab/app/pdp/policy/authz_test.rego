# app/pdp/policy/authz_test.rego
#
# Run: opa test ./policy -v

package authz_test

import rego.v1
import data.authz

# -----------------------------------------------------------------------
# Read access
# -----------------------------------------------------------------------

test_read_allowed_low_risk if {
    authz.allow with input as {
        "action": "notes:Read",
        "principal": {"id": "user:alice", "groups": []},
        "context": {"device_trust": "low-risk", "risk_score": 10, "compliant": true},
    }
}

test_read_denied_high_risk_device if {
    not authz.allow with input as {
        "action": "notes:Read",
        "principal": {"id": "user:alice", "groups": []},
        "context": {"device_trust": "high-risk", "risk_score": 10, "compliant": true},
    }
}

# -----------------------------------------------------------------------
# Write access
# -----------------------------------------------------------------------

test_write_allowed_writer_compliant if {
    authz.allow with input as {
        "action": "notes:Write",
        "principal": {"id": "user:bob", "groups": ["writer"]},
        "context": {"device_trust": "low-risk", "risk_score": 30, "compliant": true},
    }
}

test_write_denied_no_writer_group if {
    not authz.allow with input as {
        "action": "notes:Write",
        "principal": {"id": "user:charlie", "groups": ["reader"]},
        "context": {"device_trust": "low-risk", "risk_score": 10, "compliant": true},
    }
}

test_write_denied_high_risk if {
    not authz.allow with input as {
        "action": "notes:Write",
        "principal": {"id": "user:bob", "groups": ["writer"]},
        "context": {"device_trust": "high-risk", "risk_score": 30, "compliant": true},
    }
}

test_write_denied_non_compliant if {
    not authz.allow with input as {
        "action": "notes:Write",
        "principal": {"id": "user:bob", "groups": ["writer"]},
        "context": {"device_trust": "low-risk", "risk_score": 30, "compliant": false},
    }
}

test_write_denied_high_risk_score if {
    not authz.allow with input as {
        "action": "notes:Write",
        "principal": {"id": "user:bob", "groups": ["writer"]},
        "context": {"device_trust": "low-risk", "risk_score": 85, "compliant": true},
    }
}

# -----------------------------------------------------------------------
# Admin access
# -----------------------------------------------------------------------

test_admin_can_write if {
    authz.allow with input as {
        "action": "notes:Write",
        "principal": {"id": "user:admin", "groups": ["admin"]},
        "context": {"device_trust": "low-risk", "risk_score": 10, "compliant": true},
    }
}

test_admin_can_read if {
    authz.allow with input as {
        "action": "notes:Read",
        "principal": {"id": "user:admin", "groups": ["admin"]},
        "context": {"device_trust": "low-risk", "risk_score": 10, "compliant": true},
    }
}

test_admin_denied_high_risk_device if {
    not authz.allow with input as {
        "action": "notes:Write",
        "principal": {"id": "user:admin", "groups": ["admin"]},
        "context": {"device_trust": "high-risk", "risk_score": 10, "compliant": true},
    }
}

test_admin_denied_non_compliant if {
    not authz.allow with input as {
        "action": "notes:Write",
        "principal": {"id": "user:admin", "groups": ["admin"]},
        "context": {"device_trust": "low-risk", "risk_score": 10, "compliant": false},
    }
}

# -----------------------------------------------------------------------
# Default deny
# -----------------------------------------------------------------------

test_unknown_action_denied if {
    not authz.allow with input as {
        "action": "notes:Delete",
        "principal": {"id": "user:alice", "groups": []},
        "context": {"device_trust": "low-risk", "risk_score": 10, "compliant": true},
    }
}

test_empty_input_denied if {
    not authz.allow with input as {}
}
