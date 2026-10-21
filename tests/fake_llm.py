"""A scripted stand-in for an LLM, so the demo and the tests run without an API key.

It speaks the OpenAI chat-completions protocol. For each request it works out which agent is
asking (from the system prompt) and which step that agent is on (from the tool results so far).
Then it either calls a Caura tool or writes a final answer built from what the tools returned.
It answers in the native tool-calling format that all three frameworks use with this setup.
Because the answers come from real Caura responses, a run only passes when Caura does its job.

    python tests/fake_llm.py 8765
    LLM_BASE_URL=http://localhost:8765/v1 python run_demo.py --fresh
"""
import json
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SEEN = []  # every request the model received, so tests can check what the agents offered it

MEMORY_RESULT = re.compile(r'"id":"([0-9a-f-]{36})".*?"content":"((?:[^"\\]|\\.)*)"', re.S)


def flatten(content) -> str:
    if isinstance(content, list):
        return " ".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in content)
    return content or ""


def observations(messages) -> list[str]:
    """Everything the tools have returned so far, in order."""
    return [flatten(m.get("content")) for m in messages if m.get("role") == "tool"]


def memories(observation: str) -> list[tuple[str, str]]:
    """(id, content) pairs from a caura_recall result. Recall lists each hit under two keys, so drop repeats."""
    unique = {}
    for memory_id, content in MEMORY_RESULT.findall(observation):
        unique.setdefault(memory_id, json.loads(f'"{content}"'))
    return list(unique.items())


def decide(messages):
    """Return ("call", tool, args) or ("final", text) for the agent making this request."""
    system = " ".join(flatten(m.get("content")) for m in messages if m.get("role") == "system").lower()
    first_user = next(flatten(m.get("content")) for m in messages if m.get("role") == "user")
    seen = observations(messages)
    step = len(seen)

    if "researcher" in system and "Store each fact" in first_user:
        facts = [line[2:].strip() for line in first_user.splitlines() if line.startswith("- ")]
        if step < len(facts):
            return "call", "caura_write", {"content": facts[step]}
        return "final", f"Stored {len(facts)} facts."

    if "researcher" in system and "What is the pricing API rate limit" in first_user:
        if step == 0:
            return "call", "caura_recall", {"query": "pricing API rate limit"}
        hits = [c for _, c in memories(seen[0]) if "requests per minute" in c]
        return "final", hits[0] if hits else "Team memory has no answer."

    if "writer" in system:
        if step == 0:
            return "call", "caura_recall", {"query": "pricing API"}
        lines = [c for _, c in memories(seen[0])][:3]
        return "final", " ".join(lines) if lines else "Team memory has no facts yet."

    if "reviewer" in system:
        if step == 0:
            return "call", "caura_recall", {"query": "pricing API rate limit"}
        stale = [i for i, c in memories(seen[0]) if "100 requests per minute" in c]
        if stale and step == 1:
            return "call", "caura_manage", {"op": "transition", "memory_id": stale[0], "status": "outdated"}
        if step <= 2:
            return "call", "caura_write", {"content": "The pricing API rate limit is 60 requests per minute per key."}
        return "final", "Marked the old rate limit as outdated and stored the corrected limit of 60 requests per minute."

    if "editor" in system:
        hits = re.findall(r"(\d+) requests per minute", first_user)
        return "final", f"The pricing API now allows {hits[0]} requests per minute per key." if hits else "No rate limit found."

    return "final", "No script for this agent."


def reply_body(payload: dict) -> dict:
    SEEN.append(payload)
    kind, *rest = decide(payload["messages"])
    if kind == "call":
        tool, args = rest
        message = {"role": "assistant", "content": None, "tool_calls": [{
            "id": f"call_{abs(hash((tool, json.dumps(args)))) % 10**8}", "type": "function",
            "function": {"name": tool, "arguments": json.dumps(args)}}]}
        finish = "tool_calls"
    else:
        message = {"role": "assistant", "content": rest[0]}
        finish = "stop"
    return {"id": "fake", "object": "chat.completion", "created": 0, "model": payload.get("model", "fake"),
            "choices": [{"index": 0, "finish_reason": finish, "message": message}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        body = json.dumps(reply_body(payload)).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def start(port: int = 0) -> ThreadingHTTPServer:
    """Start in a background thread. Use port 0 to pick a free port."""
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1]) if len(sys.argv) > 1 else 8765), Handler).serve_forever()
