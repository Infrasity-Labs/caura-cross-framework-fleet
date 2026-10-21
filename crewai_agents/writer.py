"""Writer agent built with CrewAI, using Caura as its shared memory over MCP.

Run it alone:
    python -m crewai_agents.writer
"""
import os

os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

from crewai import LLM, Agent, Crew, Process, Task  # noqa: E402
from crewai.tools import BaseTool  # noqa: E402
from crewai_tools import MCPServerAdapter  # noqa: E402
from pydantic import BaseModel, create_model  # noqa: E402

from fleet_common.config import LLM_API_KEY, LLM_BASE_URL, LLM_MAX_TOKENS, LLM_MODEL, MCP_HEADERS, MCP_URL  # noqa: E402
from fleet_common.identity import ALLOWED_TOOLS, HIDDEN_PARAMS, Identity, bind_args, identity_for  # noqa: E402
from fleet_common.scenario import ROLE_PROMPTS, TASKS  # noqa: E402


def bind_identity(tool: BaseTool, who: Identity) -> BaseTool:
    """Wrap an MCP tool so the model never sees identity arguments and the code sets them."""
    inner_run = tool._run
    fields = {
        name: (field.annotation, field)
        for name, field in tool.args_schema.model_fields.items()
        if name not in HIDDEN_PARAMS
    }
    visible_args = create_model(f"{tool.name}_args", **fields)
    description = tool.description.split("Tool Description:", 1)[-1].strip()

    class FleetTool(BaseTool):
        name: str = tool.name
        args_schema: type[BaseModel] = visible_args

        def _run(self, **kwargs):
            return inner_run(**bind_args(tool.name, kwargs, who))

    return FleetTool(description=description)


def run(task: str, who: Identity) -> str:
    llm = LLM(model=f"openai/{LLM_MODEL}", base_url=LLM_BASE_URL, api_key=LLM_API_KEY, max_tokens=LLM_MAX_TOKENS)
    server = {"url": MCP_URL, "transport": "streamable-http", "headers": MCP_HEADERS}
    with MCPServerAdapter(server, *ALLOWED_TOOLS) as mcp_tools:
        writer = Agent(
            role="Writer",
            goal="Write launch copy that uses only facts the team has stored in shared memory",
            backstory=ROLE_PROMPTS["writer"],
            llm=llm,
            tools=[bind_identity(tool, who) for tool in mcp_tools],
            allow_delegation=False,
            verbose=False,
        )
        draft = Task(
            description=task,
            expected_output="A three-sentence launch note.",
            agent=writer,
        )
        crew = Crew(agents=[writer], tasks=[draft], process=Process.sequential, verbose=False)
        return str(crew.kickoff())


if __name__ == "__main__":
    print(run(TASKS["writer_draft"], identity_for("writer")))
