"""Unit tests for identity binding. No network needed."""
from fleet_common.identity import HIDDEN_PARAMS, Identity, bind_args, strip_schema

WHO = Identity(agent_id="researcher-1", fleet_id="team-a")


def test_write_gets_agent_fleet_and_team_visibility():
    args = bind_args("caura_write", {"content": "A fact."}, WHO)
    assert args == {"content": "A fact.", "agent_id": "researcher-1", "fleet_id": "team-a", "visibility": "scope_team"}


def test_recall_is_limited_to_the_team_fleet():
    args = bind_args("caura_recall", {"query": "limit"}, WHO)
    assert args["fleet_ids"] == ["team-a"] and args["agent_id"] == "researcher-1"


def test_manage_only_gets_the_agent_id():
    args = bind_args("caura_manage", {"op": "transition", "memory_id": "m1", "status": "outdated"}, WHO)
    assert args["agent_id"] == "researcher-1" and "fleet_id" not in args


def test_identity_the_model_supplies_is_overwritten():
    sent = {"content": "x", "agent_id": "someone-else", "fleet_id": "other-fleet", "visibility": "scope_org"}
    args = bind_args("caura_write", sent, WHO)
    assert args["agent_id"] == "researcher-1" and args["fleet_id"] == "team-a" and args["visibility"] == "scope_team"


def test_strip_schema_hides_identity_arguments():
    schema = {
        "type": "object",
        "properties": {"content": {"type": "string"}, "agent_id": {"type": "string"}, "fleet_id": {"type": "string"}},
        "required": ["content", "agent_id"],
    }
    clean = strip_schema(schema)
    assert set(clean["properties"]) == {"content"} and clean["required"] == ["content"]
    assert "agent_id" in schema["properties"]  # the original is left alone
    assert HIDDEN_PARAMS.isdisjoint(clean["properties"])
