"""Pin each agent's identity in code instead of trusting the model to pass it.

On a self-hosted Caura in standalone mode, the agent a call acts as comes from the
`agent_id` argument of the tool call. If the model fills that in, one typo puts a memory
under the wrong agent or the wrong fleet. These helpers do two things for every framework:

1. `strip_schema` hides identity arguments from the model, so it never sees them.
2. `bind_args` writes the real identity into every call, and overwrites anything the model sent.
"""
from dataclasses import dataclass
from typing import Any

from .config import AGENT_SUFFIX, FLEET_ID

# The three Caura tools the demo needs. The other nine stay out of the model's prompt.
ALLOWED_TOOLS = ("caura_write", "caura_recall", "caura_manage")

# Arguments the code sets, so the model does not see them.
HIDDEN_PARAMS = {"agent_id", "fleet_id", "fleet_ids", "visibility", "tenant_id"}


@dataclass(frozen=True)
class Identity:
    agent_id: str
    fleet_id: str


def identity_for(role: str) -> Identity:
    """Identity for a role such as "researcher". Reads FLEET_ID and AGENT_SUFFIX from the environment."""
    return Identity(agent_id=f"{role}{AGENT_SUFFIX}", fleet_id=FLEET_ID)


def bind_args(tool_name: str, args: dict[str, Any] | None, who: Identity) -> dict[str, Any]:
    """Return the tool arguments with this agent's identity written in."""
    out = {k: v for k, v in (args or {}).items() if k not in HIDDEN_PARAMS}
    out["agent_id"] = who.agent_id
    if tool_name == "caura_write":
        out["fleet_id"] = who.fleet_id
        out["visibility"] = "scope_team"  # every agent in the fleet can recall it
    elif tool_name == "caura_recall":
        out["fleet_ids"] = [who.fleet_id]
    return out


def strip_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Copy of a tool's JSON schema without the identity arguments."""
    clean = dict(schema)
    clean["properties"] = {k: v for k, v in schema.get("properties", {}).items() if k not in HIDDEN_PARAMS}
    if "required" in schema:
        clean["required"] = [r for r in schema["required"] if r not in HIDDEN_PARAMS]
    return clean
