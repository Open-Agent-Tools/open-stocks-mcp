# Kubernetes Deployment: open-stocks-mcp

This directory contains Kubernetes manifests for deploying the Open Stocks MCP server in a cluster. These manifests mirror the configuration found in the Docker Compose example.

## Prerequisites

- A Kubernetes cluster (e.g., [kind](https://kind.sigs.k8s.io/), [minikube](https://minikube.sigs.k8s.io/), [k3s](https://k3s.io/)).
- `kubectl` installed locally.
- Docker installed locally to build the image.

## Setup Instructions

### 1. Build and Load Image

First, build the Docker image locally from the project root or the Docker example directory:

```bash
# From the project root
docker build -t open-stocks-mcp:latest -f examples/open-stocks-mcp-docker/Dockerfile .
```

If you are using `kind`, load the image into your cluster:

```bash
kind load docker-image open-stocks-mcp:latest
```

If you are using `minikube`:

```bash
minikube image load open-stocks-mcp:latest
```

### 2. Prepare Credentials

Copy the secret template and fill in your Robinhood credentials:

```bash
cp secret.yaml.example secret.yaml
# Edit secret.yaml and replace REPLACE_ME values
```

**Note:** `secret.yaml` is gitignored and should never be committed.

### 3. Deploy to Kubernetes

Apply the manifests in the following order:

```bash
# 1. Create PersistentVolumeClaims for tokens and logs
kubectl apply -f pvc.yaml

# 2. Create ConfigMap for non-secret configuration
kubectl apply -f configmap.yaml

# 3. Create Secret for credentials
kubectl apply -f secret.yaml

# 4. Create Deployment and Service
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
```

Alternatively, you can apply the entire directory (excluding the `.example` file):

```bash
kubectl apply -f pvc.yaml -f configmap.yaml -f secret.yaml -f deployment.yaml -f service.yaml
```

### 4. Verify Deployment

Check the status of the pods:

```bash
kubectl get pods -l app=open-stocks-mcp
```

To test the health endpoint, use port-forwarding:

```bash
kubectl port-forward svc/open-stocks-mcp 3001:3001
```

Then in another terminal:

```bash
curl http://localhost:3001/health
```

## Teardown

To remove all resources created by these manifests:

```bash
kubectl delete -f .
```

## Storage Considerations

The `pvc.yaml` manifest omits `storageClassName` to use the cluster's default storage class. If your cluster does not have a default storage class, or you wish to use a specific one (e.g., for static provisioning), edit `pvc.yaml` to include the appropriate `storageClassName`.

## Scope

These Kubernetes artifacts are additive to the project and provide an alternative to Docker Compose. Existing CI/CD workflows remain unchanged.
