"""Reviewer agent built with LangGraph, using Caura as its shared memory over MCP.

Run it alone:
    python -m langgraph_agents.reviewer
"""
import asyncio

from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI

from fleet_common.config import LLM_API_KEY, LLM_BASE_URL, LLM_MAX_TOKENS, LLM_MODEL, MCP_HEADERS, MCP_URL
from fleet_common.identity import ALLOWED_TOOLS, Identity, bind_args, identity_for, strip_schema
from fleet_common.scenario import ROLE_PROMPTS, TASKS


async def run(task: str, who: Identity) -> str:
    async def bind_identity(request, handler):
        """Interceptor: runs before every MCP tool call and writes this agent's identity in."""
        return await handler(request.override(args=bind_args(request.name, request.args, who)))

    client = MultiServerMCPClient(
        {"caura": {"url": MCP_URL, "transport": "streamable_http", "headers": MCP_HEADERS}},
        tool_interceptors=[bind_identity],
    )
    tools = [tool for tool in await client.get_tools() if tool.name in ALLOWED_TOOLS]
    for tool in tools:
        tool.args_schema = strip_schema(tool.args_schema)  # hide identity arguments from the model

    llm = ChatOpenAI(model=LLM_MODEL, base_url=LLM_BASE_URL, api_key=LLM_API_KEY, max_tokens=LLM_MAX_TOKENS)
    agent = create_agent(llm, tools, system_prompt=ROLE_PROMPTS["reviewer"])
    result = await agent.ainvoke({"messages": [("user", task)]}, config={"recursion_limit": 25})
    return str(result["messages"][-1].content)


if __name__ == "__main__":
    print(asyncio.run(run(TASKS["reviewer_check"], identity_for("reviewer"))))
