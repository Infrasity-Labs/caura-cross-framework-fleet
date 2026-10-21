# Caura shared memory for OpenAI Agents SDK agents

This folder connects an agent built with the [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/) to Caura through MCP. The agent saves facts to a shared fleet memory and recalls what other agents saved, even when those agents run on other frameworks.

## Connect the agent to Caura

Caura serves MCP over streamable HTTP, so the SDK's `MCPServerStreamableHttp` connects with a URL and a key. [`researcher.py`](researcher.py) subclasses it to write the agent's identity into every call:

```python
class CauraFleetServer(MCPServerStreamableHttp):
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
```

`list_tools` offers the model three Caura tools and hides the identity arguments. `call_tool` writes the real `agent_id` and `fleet_id` into each call. Then the agent uses the server like any other MCP server:

```python
async with CauraFleetServer(who) as caura:
    agent = Agent(name="Researcher", instructions=ROLE_PROMPTS["researcher"], model=model, mcp_servers=[caura])
    result = await Runner.run(agent, task, max_turns=12)
```

## Use OpenRouter or another provider

The model comes from any OpenAI-compatible endpoint. Set `LLM_BASE_URL`, `LLM_API_KEY` and `LLM_MODEL`. The file builds an `OpenAIChatCompletionsModel` around an `AsyncOpenAI` client and turns tracing off, because tracing would try to reach OpenAI.

## Run it on its own

Start Caura with `scripts/start-caura.sh` from the repo root, set your model variables, then:

```bash
python -m openai_agents_sdk.researcher store     # saves three facts from the v1 pricing notes
python -m openai_agents_sdk.researcher answer    # answers the rate limit from team memory
```

Run `store` first. After the reviewer in [`langgraph_agents/`](../langgraph_agents/) has corrected the memory, `answer` returns 60 requests per minute.
