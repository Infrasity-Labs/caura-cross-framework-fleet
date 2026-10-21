"""Run the full handoff: three agents on three frameworks share one Caura fleet.

    python run_demo.py            # uses the fleet in FLEET_ID (default: launch-team)
    python run_demo.py --fresh    # new agent names and a new fleet, so reruns start from empty memory

Steps:
  1. Researcher (OpenAI Agents SDK) stores facts from the v1 pricing notes.
  2. Writer (CrewAI) recalls them and drafts a launch note.
  3. Reviewer (LangGraph) reads the October changelog, retires the wrong rate limit and stores the right one.
  4. Researcher (OpenAI Agents SDK) is asked the rate limit again and should now answer 60, not 100.
  5. Optional (--with-rail): Editor (LangGraph + Caura Rail) writes the final announcement over REST.
"""
import argparse
import asyncio
import os
import secrets
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fresh", action="store_true", help="use new agent names and a new fleet")
    parser.add_argument("--with-rail", action="store_true", help="add the LangGraph + Caura Rail editor step")
    args = parser.parse_args()

    # Settings are read when fleet_common.config is imported, so set the environment first.
    if args.fresh:
        tag = secrets.token_hex(2)
        os.environ["AGENT_SUFFIX"] = f"-{tag}"
        os.environ["FLEET_ID"] = f"launch-team-{tag}"

    from crewai_agents import writer
    from fleet_common.identity import identity_for
    from fleet_common.scenario import TASKS
    from langgraph_agents import reviewer
    from langgraph_rail import editor
    from openai_agents_sdk import researcher

    def step(number: int, title: str, text: str) -> None:
        print(f"\n[{number}] {title}\n{text.strip()}")

    step(1, "Researcher (OpenAI Agents SDK) stores the v1 facts",
         asyncio.run(researcher.run(TASKS["researcher_store"], identity_for("researcher"))))
    step(2, "Writer (CrewAI) drafts from team memory",
         writer.run(TASKS["writer_draft"], identity_for("writer")))
    step(3, "Reviewer (LangGraph) checks memory against the October changelog",
         asyncio.run(reviewer.run(TASKS["reviewer_check"], identity_for("reviewer"))))
    answer = asyncio.run(researcher.run(TASKS["researcher_answer"], identity_for("researcher")))
    step(4, "Researcher (OpenAI Agents SDK) is asked the rate limit again", answer)
    if args.with_rail:
        step(5, "Editor (LangGraph + Caura Rail) writes the announcement",
             editor.run(TASKS["editor_final"], identity_for("editor")))

    reached = "60" in answer and "100" not in answer
    print("\nResult:", "the correction reached the Agents SDK agent" if reached else "the old rate limit is still in use")
    return 0 if reached else 1


if __name__ == "__main__":
    sys.exit(main())
