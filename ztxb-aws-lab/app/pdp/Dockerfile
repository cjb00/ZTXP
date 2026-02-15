# app/pdp/Dockerfile

FROM openpolicyagent/opa:0.64.1

# Copy policy bundle into the image
COPY policy /policy

EXPOSE 8181

# Run OPA in server mode, load the entire policy directory
CMD ["run", "--server", "--addr", ":8181", "/policy"]
