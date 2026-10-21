# Caura Rail with LangGraph: shared memory around a graph node

This folder uses [Caura Rail](https://github.com/caura-ai/caura-rail), Caura's Python and TypeScript SDK, inside a LangGraph node. Rail talks to Caura over REST, so this example needs no MCP client.

## Where Rail fits

Rail wraps one turn of an agent. Before your model runs, it recalls the fleet's rules and the facts that match the request. After the model replies, it can write facts back. Your code keeps control of the model call.

A LangGraph node is a plain Python function, so that fits. [`editor.py`](editor.py) puts the recall step around the model call:

```python
def write_announcement(state: State) -> State:
    with rail.turn(state["request"]) as turn:
        prompt = f"{turn.context.text}\n\nRequest: {state['request']}"
        reply = llm.invoke([("system", ROLE_PROMPTS["editor"]), ("user", prompt)]).content
        turn.reply = str(reply)
    return {"request": state["request"], "announcement": turn.reply}
```

`turn.context.text` holds the governance rules first, then the recalled facts, already formatted for a prompt.

## Set up the scope

```python
scope = MemoryScope(agent_id=who.agent_id, fleet_id=who.fleet_id, visibility=Visibility.TEAM)
with RestMemoryStore(base_url=CAURA_URL, api_key=CAURA_API_KEY) as store:
    rail = Rail(store, scope, extractor=lambda message, reply: [])
```

The scope names the agent and the fleet it shares. The extractor returns no facts, so this editor only reads. Rail's default extractor stores only user lines that start with phrases such as `Remember:`, so a node that should write facts needs its own extractor.

The editor sees the current rate limit and not the retired one, because recall returns active memories only.

## Requirements

Rail needs a Caura server at release 2.47.0 or later. `scripts/start-caura.sh` starts 3.34.0.

## Run it on its own

Start Caura with `scripts/start-caura.sh` from the repo root and set your model variables. The editor reads what the other agents saved, so run the researcher and reviewer first, or use `python run_demo.py --fresh --with-rail` from the repo root. Then:

```bash
python -m langgraph_rail.editor
```

For the full guide, see the [Rail repository](https://github.com/caura-ai/caura-rail).
