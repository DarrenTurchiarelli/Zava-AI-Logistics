"""
Validate that Customer Service and Dispatcher agents have tools registered.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

sys.path.insert(0, str(Path(__file__).parent.parent))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

load_dotenv(override=True)

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
CUSTOMER_SERVICE_AGENT_ID = os.getenv("CUSTOMER_SERVICE_AGENT_ID")
DISPATCHER_AGENT_ID = os.getenv("DISPATCHER_AGENT_ID")

# Minimum tools expected per agent
REQUIRED_TOOLS = {
    "Customer Service Agent": (CUSTOMER_SERVICE_AGENT_ID, 4),
    "Dispatcher Agent":       (DISPATCHER_AGENT_ID,       3),
}


def validate_agent_tools():
    print("=" * 70)
    print("Validating Agent Tool Registration")
    print("=" * 70)
    print()

    if not AZURE_OPENAI_ENDPOINT:
        print("ERROR: AZURE_OPENAI_ENDPOINT not set")
        return False

    credential = DefaultAzureCredential()
    token_provider = get_bearer_token_provider(credential, "https://cognitiveservices.azure.com/.default")
    client = AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        azure_ad_token_provider=token_provider,
        api_version="2024-05-01-preview",
    )

    all_ok = True

    for label, (agent_id, min_tools) in REQUIRED_TOOLS.items():
        if not agent_id:
            print(f"  SKIP  {label}: env var not set")
            continue

        try:
            agent = client.beta.assistants.retrieve(agent_id)
            tool_count = len(agent.tools) if agent.tools else 0
            tools_names = [t.function.name for t in agent.tools if hasattr(t, "function")]

            if tool_count >= min_tools:
                print(f"  OK    {label}: {tool_count} tools registered")
                for name in tools_names:
                    print(f"          - {name}")
            else:
                print(f"  FAIL  {label}: expected >= {min_tools} tools, found {tool_count}")
                all_ok = False
        except Exception as e:
            print(f"  ERROR {label}: {e}")
            all_ok = False

        print()

    if all_ok:
        print("All agents validated successfully")
    else:
        print("Validation failed - run register_agent_tools_openai.py to fix")

    return all_ok


if __name__ == "__main__":
    sys.exit(0 if validate_agent_tools() else 1)