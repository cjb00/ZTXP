# app/pdp/policy/authz.rego

package authz

# Default deny
default allow = false

# Anyone can read notes
allow {
  input.action == "notes:Read"
}

# Writers can write, as long as device is not marked high-risk
allow {
  input.action == "notes:Write"
  user_in_group("writer")
  not high_risk_device
}

user_in_group(g) {
  some idx
  g == input.principal.groups[idx]
}

high_risk_device {
  input.context.device_trust == "high-risk"
}
