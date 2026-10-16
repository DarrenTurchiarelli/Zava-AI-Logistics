"""Publish versioned Foundry toolboxes for the Zava logistics APIs."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    OpenApiFunctionDefinition,
    OpenApiProjectConnectionAuthDetails,
    OpenApiProjectConnectionSecurityScheme,
    OpenApiToolboxTool,
)
from azure.identity import AzureCliCredential


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.interfaces.web.routes.agent_tools import build_openapi_spec


TOOLBOXES = {
    "read": {
        "name": "zava-logistics-read",
        "connection": "zava-logistics-read-api",
        "description": "Read-only parcel, driver, dispatch, and performance operations for Zava agents.",
    },
    "write": {
        "name": "zava-logistics-write",
        "connection": "zava-logistics-write-api",
        "description": "Controlled manifest creation and delivery-status mutation operations for Zava agents.",
    },
}


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-endpoint",
        default=os.getenv("AZURE_AI_PROJECT_ENDPOINT") or os.getenv("FOUNDRY_PROJECT_ENDPOINT"),
        required=not (os.getenv("AZURE_AI_PROJECT_ENDPOINT") or os.getenv("FOUNDRY_PROJECT_ENDPOINT")),
    )
    parser.add_argument("--app-base-url", required=True)
    parser.add_argument("--tenant-id", default=os.getenv("AZURE_TENANT_ID"))
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    credential = AzureCliCredential(tenant_id=args.tenant_id)
    created: list[tuple[str, str, str]] = []

    try:
        with AIProjectClient(endpoint=args.project_endpoint, credential=credential) as project:
            for access, definition in TOOLBOXES.items():
                connection = project.connections.get(definition["connection"])
                auth = OpenApiProjectConnectionAuthDetails(
                    security_scheme=OpenApiProjectConnectionSecurityScheme(
                        project_connection_id=connection.id,
                    )
                )
                openapi = OpenApiFunctionDefinition(
                    name=f"zava-logistics-{access}-api",
                    description=definition["description"],
                    spec=build_openapi_spec(args.app_base_url, access),
                    auth=auth,
                )
                toolbox = project.toolboxes.create_version(
                    name=definition["name"],
                    description=definition["description"],
                    tools=[
                        OpenApiToolboxTool(
                            name=f"zava-logistics-{access}-api",
                            description=definition["description"],
                            openapi=openapi,
                        )
                    ],
                    metadata={"application": "zava-logistics", "access": access},
                )
                endpoint = (
                    f"{args.project_endpoint.rstrip('/')}/toolboxes/{toolbox.name}"
                    f"/versions/{toolbox.version}/mcp?api-version=v1"
                )
                created.append((toolbox.name, str(toolbox.version), endpoint))
    finally:
        credential.close()

    for name, version, endpoint in created:
        print(f"{name}\tversion={version}\t{endpoint}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())