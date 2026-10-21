"""Connection settings shared by every example. Everything comes from environment variables."""
import os

# Where Caura runs. The default matches `scripts/start-caura.sh` (self-hosted, standalone mode).
CAURA_URL = os.getenv("CAURA_URL", "http://localhost:8000").rstrip("/")
CAURA_API_KEY = os.getenv("CAURA_API_KEY", "standalone")
MCP_URL = f"{CAURA_URL}/mcp"
MCP_HEADERS = {"X-API-Key": CAURA_API_KEY}

# The model the agents think with. Any OpenAI-compatible endpoint works:
# OpenRouter (default), a local Ollama server, or another provider.
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY") or os.getenv("OPENROUTER_API_KEY") or "not-set"
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-5.4-mini")
# Cap on tokens per model reply. Without it, providers such as OpenRouter reserve the model's full
# output limit against your balance and refuse the call when credit is low.
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "4096"))

# The team shares one fleet. Change it to start from an empty memory.
FLEET_ID = os.getenv("FLEET_ID", "launch-team")
AGENT_SUFFIX = os.getenv("AGENT_SUFFIX", "")
