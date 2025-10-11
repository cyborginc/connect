# run.py
import os, sys, asyncio, json, traceback
from agents import Agent, Runner, ModelSettings
from agents.tool import HostedMCPTool
from openai.types.shared.reasoning import Reasoning

MANIFEST_URL = "https://unspecifically-commeasurable-dayle.ngrok-free.dev/manifest.json"

def assert_env():
    key = os.environ.get("OPENAI_API_KEY")
    if not key or not key.startswith("sk-"):
        print("❌ OPENAI_API_KEY not set (or malformed). Do: export OPENAI_API_KEY=sk-XXXX", flush=True)
        sys.exit(1)

def make_agent():
    mcp = HostedMCPTool(
        tool_config={
            "type": "mcp",
            "server_label": "cyborgdb",
            "allowed_tools": ["query_documents"],
            "require_approval": "never",
            "server_url": MANIFEST_URL,
            # "headers": {"Authorization": "Bearer <TOKEN>"},
        }
    )
    return Agent(
        name="Agent",
        instructions=(
            "Use the MCP tool `cyborgdb.query_documents` to answer questions from our indexed docs.\n"
            "Call it with: { \"input\": <the user's question> }.\n"
            "Return a 2–3 bullet summary; if no results, say so and suggest a better query."
        ),
        model="gpt-5",
        tools=[mcp],
        model_settings=ModelSettings(store=True, reasoning=Reasoning(effort="low")),
    )

async def run_once(question: str):
    print(f"🔹 Starting run for query: {question}", flush=True)
    agent = make_agent()
    try:
        res = await Runner.run(
            agent,
            input=[{"role": "user", "content": [{"type": "input_text", "text": question}]}],
        )
        # Print everything we can
        print("🔹 Runner returned.", flush=True)
        try:
            print("final_output_as(str):", res.final_output_as(str))
        except Exception as e:
            print("final_output_as(str) failed:", e)
        print("raw result object dir():", [a for a in dir(res) if not a.startswith("_")])
        # Some versions expose output_text or final_output:
        text = getattr(res, "final_output", None) or getattr(res, "output_text", None)
        print("\n=== OUTPUT ===\n", text, flush=True)
        # Also show any new items to confirm tool call happened
        if hasattr(res, "new_items"):
            print("\n=== NEW ITEMS ===")
            for it in res.new_items:
                try:
                    print(it.model_dump_json(indent=2))
                except Exception:
                    print(it)
    except Exception as e:
        print("❌ Exception during Runner.run:")
        traceback.print_exc()
        # Extra hint: turn on verbose HTTP logging if needed
        print("\nTip: set OPENAI_LOG=debug for HTTP traces (export OPENAI_LOG=debug).", flush=True)

if __name__ == "__main__":
    assert_env()
    q = " ".join(sys.argv[1:]) or "encryption at rest vs in transit"
    print("MCP manifest:", MANIFEST_URL, flush=True)
    asyncio.run(run_once(q))
