"""Researcher agent built with the OpenAI Agents SDK, using Caura as its shared memory over MCP.

Run it alone:
    python -m openai_agents_sdk.researcher store      # save the facts from the v1 pricing notes
    python -m openai_agents_sdk.researcher answer     # answer a question from team memory
"""
import asyncio
import sys

from agents import Agent, ModelSettings, OpenAIChatCompletionsModel, Runner, set_tracing_disabled
from agents.mcp import MCPServerStreamableHttp
from openai import AsyncOpenAI

from fleet_common.config import LLM_API_KEY, LLM_BASE_URL, LLM_MAX_TOKENS, LLM_MODEL, MCP_HEADERS, MCP_URL
from fleet_common.identity import ALLOWED_TOOLS, Identity, bind_args, identity_for, strip_schema
from fleet_common.scenario import ROLE_PROMPTS, TASKS


class CauraFleetServer(MCPServerStreamableHttp):
    """Caura's MCP server, with this agent's identity written into every call."""

    def __init__(self, who: Identity):
        super().__init__(
            params={"url": MCP_URL, "headers": MCP_HEADERS},
            name="caura",
            cache_tools_list=True,
            client_session_timeout_seconds=60,
        )
        self.who = who

    async def list_tools(self, run_context=None, agent=None):
        tools = await super().list_tools(run_context, agent)
        return [
            tool.model_copy(update={"inputSchema": strip_schema(tool.inputSchema)})
            for tool in tools
            if tool.name in ALLOWED_TOOLS
        ]

    async def call_tool(self, tool_name, arguments, meta=None):
        return await super().call_tool(tool_name, bind_args(tool_name, arguments, self.who), meta)


async def run(task: str, who: Identity) -> str:
    set_tracing_disabled(True)  # tracing would try to reach OpenAI
    model = OpenAIChatCompletionsModel(
        model=LLM_MODEL,
        openai_client=AsyncOpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY),
    )
    async with CauraFleetServer(who) as caura:
        agent = Agent(
            name="Researcher",
            instructions=ROLE_PROMPTS["researcher"],
            model=model,
            model_settings=ModelSettings(max_tokens=LLM_MAX_TOKENS),
            mcp_servers=[caura],
        )
        result = await Runner.run(agent, task, max_turns=12)
    return str(result.final_output)


if __name__ == "__main__":
    task = TASKS["researcher_store" if (sys.argv[1:] or ["store"])[0] == "store" else "researcher_answer"]
    print(asyncio.run(run(task, identity_for("researcher"))))
