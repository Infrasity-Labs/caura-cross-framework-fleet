# Caura shared memory for CrewAI agents

This folder connects a [CrewAI](https://docs.crewai.com) agent to Caura through MCP. The agent recalls what other agents saved to a shared fleet memory, even when those agents run on other frameworks.

## Connect the agent to Caura

CrewAI's `MCPServerAdapter` takes the server settings, followed by the names of the tools you want. [`writer.py`](writer.py) asks for three of Caura's tools:

```python
server = {"url": MCP_URL, "transport": "streamable-http", "headers": MCP_HEADERS}
with MCPServerAdapter(server, *ALLOWED_TOOLS) as mcp_tools:
    writer = Agent(
        role="Writer",
        goal="Write launch copy that uses only facts the team has stored in shared memory",
        backstory=ROLE_PROMPTS["writer"],
        llm=llm,
        tools=[bind_identity(tool, who) for tool in mcp_tools],
    )
```

`bind_identity` wraps each MCP tool in a CrewAI `BaseTool`. The wrapper removes `agent_id`, `fleet_id` and the other identity arguments from the schema the model sees, and writes the real values into every call. The model cannot put a memory under the wrong agent or fleet.

## Use OpenRouter or another provider

CrewAI talks to models through LiteLLM. Any OpenAI-compatible endpoint works with the `openai/` prefix and a base URL:

```python
llm = LLM(model=f"openai/{LLM_MODEL}", base_url=LLM_BASE_URL, api_key=LLM_API_KEY)
```

For OpenRouter, `LLM_MODEL` is the OpenRouter model name, for example `openai/gpt-5.4-mini`. The file also turns CrewAI telemetry off.

## Run it on its own

Start Caura with `scripts/start-caura.sh` from the repo root and set your model variables. The writer needs facts to recall, so run the researcher's `store` command from [`openai_agents_sdk/`](../openai_agents_sdk/) first. Then:

```bash
python -m crewai_agents.writer
```
