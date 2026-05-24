from pathlib import Path

import pytest

K8S_DIR = Path("examples/kubernetes")
DEPLOYMENT = K8S_DIR / "deployment.yaml"
SERVICE = K8S_DIR / "service.yaml"
CONFIGMAP = K8S_DIR / "configmap.yaml"
PVC = K8S_DIR / "persistentvolumeclaim.yaml"
KUSTOMIZATION = K8S_DIR / "kustomization.yaml"
SECRET_EXAMPLE = K8S_DIR / "secret.yaml.example"
K8S_README = K8S_DIR / "README.md"
ROOT_README = Path("README.md")


@pytest.mark.unit
@pytest.mark.journey_system
def test_kubernetes_manifest_files_exist():
    for path in [DEPLOYMENT, SERVICE, CONFIGMAP, PVC, KUSTOMIZATION, SECRET_EXAMPLE]:
        assert path.exists(), f"Expected {path} to exist"


@pytest.mark.unit
@pytest.mark.journey_system
def test_deployment_manifest_content():
    text = DEPLOYMENT.read_text(encoding="utf-8")
    required = [
        "kind: Deployment",
        "open-stocks-mcp-server",
        "--transport",
        "http",
        "--host",
        "0.0.0.0",
        "--port",
        "3001",
        "/health",
        "runAsUser: 1001",
        "configMapRef",
        "secretRef",
        "/home/mcp/.tokens",
        "/home/mcp/.local/state/mcp-servers/logs",
    ]
    for token in required:
        assert token in text, f"Expected '{token}' in deployment.yaml"


@pytest.mark.unit
@pytest.mark.journey_system
def test_service_manifest_content():
    text = SERVICE.read_text(encoding="utf-8")
    assert "kind: Service" in text
    assert "3001" in text


@pytest.mark.unit
@pytest.mark.journey_system
def test_secret_example_content():
    text = SECRET_EXAMPLE.read_text(encoding="utf-8")
    assert "ROBINHOOD_USERNAME" in text
    assert "ROBINHOOD_PASSWORD" in text
    # Must not contain real-looking credential values
    assert (
        "your_email@example.com" not in text
        or "placeholder" in text.lower()
        or "example" in text.lower()
    )
    # Should not have real passwords
    for suspicious in ["my_password", "secretpassword123", "hunter2"]:
        assert suspicious not in text


@pytest.mark.unit
@pytest.mark.journey_system
def test_kubernetes_readme_exists():
    assert K8S_README.exists(), "Expected examples/kubernetes/README.md to exist"


@pytest.mark.unit
@pytest.mark.journey_system
def test_kubernetes_readme_content():
    text = K8S_README.read_text(encoding="utf-8")
    required_commands = [
        "kubectl apply --dry-run=client -k examples/kubernetes",
        "kubectl apply -k examples/kubernetes",
        "kubectl port-forward service/open-stocks-mcp 3001:3001",
        "curl http://localhost:3001/health",
    ]
    for cmd in required_commands:
        assert cmd in text, f"Expected '{cmd}' in kubernetes README"
    assert "ROBINHOOD_USERNAME" in text
    assert "ROBINHOOD_PASSWORD" in text


@pytest.mark.unit
@pytest.mark.journey_system
def test_root_readme_links_to_kubernetes():
    text = ROOT_README.read_text(encoding="utf-8")
    assert "examples/kubernetes" in text, (
        "Expected root README.md to link to examples/kubernetes"
    )
