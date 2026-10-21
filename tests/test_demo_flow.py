"""Plays the whole story against a running Caura (scripts/start-caura.sh) with the scripted model.

The scripted model builds every answer from what Caura returns, so these tests pass only when
the agents really share memory across the three frameworks.
"""
import asyncio
import json
import os

import httpx
import pytest
from agents.mcp import MCPServerStreamableHttp

from crewai_agents import writer
from fleet_common.config import CAURA_URL, FLEET_ID, MCP_HEADERS, MCP_URL
from fleet_common.identity import ALLOWED_TOOLS, HIDDEN_PARAMS, identity_for
from fleet_common.scenario import TASKS
from langgraph_agents import reviewer
from langgraph_rail import editor
from openai_agents_sdk import researcher
from tests import fake_llm


def caura_is_up() -> bool:
    try:
        return httpx.get(f"{CAURA_URL}/api/v1/health", timeout=3).status_code == 200
    except httpx.HTTPError:
        return False


pytestmark = pytest.mark.skipif(not caura_is_up(), reason="start Caura first: scripts/start-caura.sh")


@pytest.fixture(scope="module")
def story():
    """Play every step once and keep each step's output."""
    out = {}
    out["stored"] = asyncio.run(researcher.run(TASKS["researcher_store"], identity_for("researcher")))
    out["draft"] = writer.run(TASKS["writer_draft"], identity_for("writer"))
    out["review"] = asyncio.run(reviewer.run(TASKS["reviewer_check"], identity_for("reviewer")))
    out["answer"] = asyncio.run(researcher.run(TASKS["researcher_answer"], identity_for("researcher")))
    out["announcement"] = editor.run(TASKS["editor_final"], identity_for("editor"))
    return out


async def recall_as(agent_id: str, query: str) -> list[dict]:
    async with MCPServerStreamableHttp(params={"url": MCP_URL, "headers": MCP_HEADERS}, client_session_timeout_seconds=60) as server:
        result = await server.call_tool("caura_recall", {"agent_id": agent_id, "fleet_ids": [FLEET_ID], "query": query})
    return json.loads(result.content[0].text)["results"]


def test_researcher_stored_three_facts(story):
    assert "3" in story["stored"]


def test_writer_on_crewai_sees_what_the_agents_sdk_researcher_stored(story):
    assert "100 requests per minute" in story["draft"]
    assert "10,000 calls" in story["draft"]
    assert "5 minutes" in story["draft"]


def test_correction_from_langgraph_reaches_the_agents_sdk_agent(story):
    assert "60" in story["answer"] and "100" not in story["answer"]


def test_rail_editor_over_rest_sees_only_the_current_limit(story):
    assert "60" in story["announcement"] and "100" not in story["announcement"]


def test_each_memory_is_attributed_to_the_agent_that_wrote_it(story):
    suffix = os.environ["AGENT_SUFFIX"]
    hits = asyncio.run(recall_as(f"auditor{suffix}", "pricing API"))
    authors = {hit["content"]: hit["agent_id"] for hit in hits}
    assert authors["The pricing API free tier includes 10,000 calls per month."] == f"researcher{suffix}"
    assert authors["The pricing API rate limit is 60 requests per minute per key."] == f"reviewer{suffix}"
    assert not any("100 requests per minute" in content for content in authors)


def test_every_framework_offers_the_model_three_tools_and_no_identity_arguments(story):
    offered = [request["tools"] for request in fake_llm.SEEN if request.get("tools")]
    assert len(offered) >= 8  # researcher x2 runs, writer, reviewer, each with several model calls
    for tools in offered:
        assert {tool["function"]["name"] for tool in tools} == set(ALLOWED_TOOLS)
        for tool in tools:
            assert HIDDEN_PARAMS.isdisjoint(tool["function"]["parameters"].get("properties", {}))
