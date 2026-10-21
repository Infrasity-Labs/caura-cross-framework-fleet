"""Test setup. Runs before any test module imports the example code, which reads settings at import time."""
import os
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

TAG = secrets.token_hex(2)  # a fresh fleet and fresh agent names for every test run
os.environ["AGENT_SUFFIX"] = f"-{TAG}"
os.environ["FLEET_ID"] = f"test-fleet-{TAG}"
os.environ["LLM_API_KEY"] = "fake"

from tests import fake_llm  # noqa: E402

SERVER = fake_llm.start()  # scripted model on a free local port
os.environ["LLM_BASE_URL"] = f"http://127.0.0.1:{SERVER.server_port}/v1"
