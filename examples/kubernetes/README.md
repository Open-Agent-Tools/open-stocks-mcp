# Kubernetes Deployment — Open Stocks MCP

Run the Open Stocks MCP server in a Kubernetes cluster using the Kustomize manifests in this directory.

## Prerequisites

- `kubectl` configured for a running cluster
- A container image `open-stocks-mcp:latest` accessible to the cluster (see [Build the image](#build-the-image))
- Robinhood credentials (and optionally Schwab credentials)

## Files

| File | Purpose |
|------|---------|
| `deployment.yaml` | Deployment — HTTP transport, `/health` probes, non-root UID 1001 |
| `service.yaml` | ClusterIP Service exposing port 3001 |
| `configmap.yaml` | Non-secret runtime config (`LOG_LEVEL`, `ENABLED_BROKERS`, etc.) |
| `persistentvolumeclaim.yaml` | 1 Gi PVC for token and log persistence |
| `kustomization.yaml` | Kustomize entry point (excludes the Secret — create it manually) |
| `secret.yaml.example` | Template for the required Kubernetes Secret |

## Build the image

The manifests reference `open-stocks-mcp:latest`. Build and load or push the image to wherever your cluster pulls from:

```bash
# Build locally (same Dockerfile as the Docker Compose example)
docker build -t open-stocks-mcp:latest examples/open-stocks-mcp-docker/

# For kind or k3d: load directly
kind load docker-image open-stocks-mcp:latest
# or
k3d image import open-stocks-mcp:latest

# For a remote registry: tag and push
docker tag open-stocks-mcp:latest registry.example.com/open-stocks-mcp:latest
docker push registry.example.com/open-stocks-mcp:latest
# Then update deployment.yaml image field accordingly
```

## Create the Secret

The Secret is intentionally excluded from `kustomization.yaml` to prevent placeholder values from being applied accidentally. Create it once before deploying:

```bash
kubectl create secret generic open-stocks-mcp-secrets \
  --from-literal=ROBINHOOD_USERNAME='your-email@example.com' \
  --from-literal=ROBINHOOD_PASSWORD='your-password'
```

For Schwab credentials, add them to the same secret:

```bash
kubectl create secret generic open-stocks-mcp-secrets \
  --from-literal=ROBINHOOD_USERNAME='your-email@example.com' \
  --from-literal=ROBINHOOD_PASSWORD='your-password' \
  --from-literal=SCHWAB_API_KEY='your-api-key' \
  --from-literal=SCHWAB_APP_SECRET='your-app-secret' \
  --from-literal=SCHWAB_CALLBACK_URL='https://127.0.0.1:8182/' \
  --from-literal=SCHWAB_TOKEN_PATH='/home/mcp/.tokens/schwab_token.json'
```

Alternatively, copy `secret.yaml.example` to `secret.yaml`, fill in real values, apply it, and then delete the file — never commit `secret.yaml` to version control.

## Secrets model

| Secret key | Required | Description |
|-----------|----------|-------------|
| `ROBINHOOD_USERNAME` | Yes | Robinhood account email |
| `ROBINHOOD_PASSWORD` | Yes | Robinhood account password |
| `SCHWAB_API_KEY` | No | Schwab developer API key |
| `SCHWAB_APP_SECRET` | No | Schwab app secret |
| `SCHWAB_CALLBACK_URL` | No | OAuth callback URL (default: `https://127.0.0.1:8182/`) |
| `SCHWAB_TOKEN_PATH` | No | Path for Schwab token storage |

Non-secret configuration lives in `configmap.yaml`: `LOG_LEVEL`, `ENABLED_BROKERS`, `DEFAULT_BROKER`, `MCP_SERVER_NAME`.

## Validate (dry run)

```bash
kubectl apply --dry-run=client -k examples/kubernetes
```

This validates manifest syntax and object structure without creating any resources.

## Deploy

```bash
kubectl apply -k examples/kubernetes
```

Check that the pod starts:

```bash
kubectl get pods -l app=open-stocks-mcp
kubectl get service open-stocks-mcp
```

Watch logs during first startup (Robinhood device verification may appear):

```bash
kubectl logs -f -l app=open-stocks-mcp
```

## Health check

Forward the service port and hit the health endpoint:

```bash
kubectl port-forward service/open-stocks-mcp 3001:3001
curl http://localhost:3001/health
```

A healthy server returns HTTP 200 with `{"status": "ok", ...}`.

## Persistence

Session tokens and logs are stored on a PVC mounted at:

- `/home/mcp/.tokens` — Robinhood pickle session (subPath: `tokens`)
- `/home/mcp/.local/state/mcp-servers/logs` — application logs (subPath: `logs`)

The PVC keeps state across pod restarts. **Pin `replicas: 1`** (the default) — Robinhood treats each new IP/session as a new device, which triggers MFA from a server with no terminal.

## Cleanup

```bash
kubectl delete -k examples/kubernetes
kubectl delete secret open-stocks-mcp-secrets
# Optionally delete the PVC (this erases token/log data):
kubectl delete pvc open-stocks-mcp-data
```

## Notes

- CI workflow configuration (`.github/workflows/**`, etc.) is intentionally out of scope for these Kubernetes artifacts. Cluster image builds and deployment pipelines are operator-managed.
- The Deployment uses HTTP transport (`--transport http`), not stdio — liveness and readiness probes use `httpGet /health` on port 3001.
