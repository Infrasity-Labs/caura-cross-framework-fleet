# Caura shared memory for LangGraph agents (MCP)

This folder connects a [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview) agent to Caura through MCP. The agent reads the shared fleet memory, retires a fact that is out of date, and stores the corrected one. Agents on other frameworks see the change on their next recall.

## Connect the agent to Caura

`langchain-mcp-adapters` gives LangGraph an MCP client with tool interceptors. An interceptor runs before every tool call, which is the place to write the agent's identity into the arguments. [`reviewer.py`](reviewer.py):

```python
async def bind_identity(request, handler):
    return await handler(request.override(args=bind_args(request.name, request.args, who)))

client = MultiServerMCPClient(
    {"caura": {"url": MCP_URL, "transport": "streamable_http", "headers": MCP_HEADERS}},
    tool_interceptors=[bind_identity],
)
tools = [tool for tool in await client.get_tools() if tool.name in ALLOWED_TOOLS]
for tool in tools:
    tool.args_schema = strip_schema(tool.args_schema)  # hide identity arguments from the model

agent = create_agent(llm, tools, system_prompt=ROLE_PROMPTS["reviewer"])
```

The model is offered three Caura tools and never sees `agent_id` or `fleet_id`.

## Correct a fact in team memory

The reviewer's prompt tells it how to retire a wrong memory and store the right one:

1. `caura_recall` finds the memory and its id.
2. `caura_manage` with `op="transition"` and `status="outdated"` retires it.
3. `caura_write` stores the corrected fact.

Recall returns active memories only, so every agent that recalls afterwards gets the corrected fact.

## Use OpenRouter or another provider

`ChatOpenAI` accepts any OpenAI-compatible endpoint through `base_url`. Set `LLM_BASE_URL`, `LLM_API_KEY` and `LLM_MODEL`.

## Run it on its own

Start Caura with `scripts/start-caura.sh` from the repo root and set your model variables. Run the researcher's `store` command from [`openai_agents_sdk/`](../openai_agents_sdk/) first, so there is a rate limit to correct. Then:

```bash
python -m langgraph_agents.reviewer
```

To use Caura's SDK instead of MCP inside a LangGraph node, see [`langgraph_rail/`](../langgraph_rail/).
