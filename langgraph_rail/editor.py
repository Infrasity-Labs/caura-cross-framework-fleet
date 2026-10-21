"""Editor node built with LangGraph and Caura Rail (Caura's REST SDK) instead of MCP.

Rail wraps one turn: it recalls the fleet's facts before your model runs and can write facts back
afterwards. LangGraph nodes are plain Python functions, so your code controls the model call and
Rail fits around it.

Run it alone (after the other agents have filled the fleet):
    python -m langgraph_rail.editor
"""
from typing import TypedDict

from caura_rail import MemoryScope, Rail, RestMemoryStore, Visibility
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from fleet_common.config import CAURA_API_KEY, CAURA_URL, LLM_API_KEY, LLM_BASE_URL, LLM_MAX_TOKENS, LLM_MODEL
from fleet_common.identity import Identity, identity_for
from fleet_common.scenario import ROLE_PROMPTS, TASKS


class State(TypedDict):
    request: str
    announcement: str


def build_graph(rail: Rail, llm: ChatOpenAI):
    def write_announcement(state: State) -> State:
        # Rail recalls rules and facts for this request before the model runs.
        with rail.turn(state["request"]) as turn:
            prompt = f"{turn.context.text}\n\nRequest: {state['request']}"
            reply = llm.invoke([("system", ROLE_PROMPTS["editor"]), ("user", prompt)]).content
            turn.reply = str(reply)
        return {"request": state["request"], "announcement": turn.reply}

    graph = StateGraph(State)
    graph.add_node("write_announcement", write_announcement)
    graph.set_entry_point("write_announcement")
    graph.add_edge("write_announcement", END)
    return graph.compile()


def run(task: str, who: Identity) -> str:
    scope = MemoryScope(agent_id=who.agent_id, fleet_id=who.fleet_id, visibility=Visibility.TEAM)
    llm = ChatOpenAI(model=LLM_MODEL, base_url=LLM_BASE_URL, api_key=LLM_API_KEY, max_tokens=LLM_MAX_TOKENS)
    with RestMemoryStore(base_url=CAURA_URL, api_key=CAURA_API_KEY) as store:
        # extractor returns no facts, so this editor only reads from the fleet.
        rail = Rail(store, scope, extractor=lambda message, reply: [])
        return build_graph(rail, llm).invoke({"request": task, "announcement": ""})["announcement"]


if __name__ == "__main__":
    print(run(TASKS["editor_final"], identity_for("editor")))
