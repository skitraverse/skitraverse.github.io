import pathlib
import subprocess
import time
import pytest
import requests

DOCS_DIR = pathlib.Path(__file__).parent.parent / "docs"
SERVER_URL = "http://localhost:8000"


@pytest.fixture(scope="session")
def dev_server():
    """Serve docs/ on localhost:8000 for the test session.

    If a server is already running (e.g. `make devserve`), it is left alone.
    Otherwise a temporary http.server process is started and torn down after
    all tests complete.
    """
    try:
        requests.get(SERVER_URL, timeout=1)
        yield  # already up — don't touch it
        return
    except requests.ConnectionError:
        pass

    if not DOCS_DIR.exists():
        pytest.skip("docs/ not built — run `make html` first")

    proc = subprocess.Popen(
        ["python3", "-m", "http.server", "8000", "--directory", str(DOCS_DIR)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Wait up to 5 s for the server to accept connections.
    for _ in range(20):
        try:
            requests.get(SERVER_URL, timeout=0.5)
            break
        except requests.ConnectionError:
            time.sleep(0.25)
    else:
        proc.terminate()
        pytest.fail("Static file server failed to start")

    yield

    proc.terminate()
    proc.wait()


@pytest.fixture(scope="session")
def require_dev_server(dev_server):
    """Alias kept for backward compatibility with test_order.py markers."""
