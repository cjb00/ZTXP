# app/pdp/Dockerfile

FROM openpolicyagent/opa:0.64.1

# Copy policy bundle into the image
COPY policy /policy

EXPOSE 8181

# Run OPA in server mode and load our policy package
CMD ["run", "--server", "/policy/authz.rego", "--addr", ":8181"]
