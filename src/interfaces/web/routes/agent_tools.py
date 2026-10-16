"""Authenticated HTTP gateway for Foundry toolbox operations."""

from __future__ import annotations

import hmac
import json
import os
from dataclasses import dataclass
from typing import Any, Callable

from flask import Blueprint, current_app, jsonify, request

from src.infrastructure.agents.tools.cosmos_tools import (
    create_manifest_tool,
    get_available_drivers_tool,
    get_delivery_statistics_tool,
    get_pending_parcels_for_dispatch_tool,
    get_performance_metrics_tool,
    search_parcels_by_driver_tool,
    search_parcels_by_recipient_tool,
    track_parcel_tool,
    update_delivery_status_tool,
)


agent_tools_bp = Blueprint("agent_tools", __name__)


@dataclass(frozen=True)
class ToolOperation:
    access: str
    function: Callable[..., str]
    description: str
    properties: dict[str, dict[str, Any]]
    required: tuple[str, ...] = ()


_STATE = {
    "type": "string",
    "enum": ["NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"],
    "description": "Optional Australian state code.",
}

TOOL_OPERATIONS: dict[str, ToolOperation] = {
    "track_parcel": ToolOperation(
        "read",
        track_parcel_tool,
        "Look up a parcel by tracking number and return its current status and history.",
        {"tracking_number": {"type": "string", "description": "Parcel tracking number or barcode."}},
        ("tracking_number",),
    ),
    "search_parcels_by_recipient": ToolOperation(
        "read",
        search_parcels_by_recipient_tool,
        "Search for parcels using recipient details and an optional date window.",
        {
            "recipient_name": {"type": "string"},
            "address": {"type": "string"},
            "postcode": {"type": "string", "pattern": "^[0-9]{4}$"},
            "days_back": {"type": "integer", "minimum": 1, "maximum": 365},
        },
    ),
    "search_parcels_by_driver": ToolOperation(
        "read",
        search_parcels_by_driver_tool,
        "Return parcels assigned to a driver, optionally filtered by status.",
        {
            "driver_id": {"type": "string"},
            "driver_name": {"type": "string"},
            "status": {"type": "string"},
        },
    ),
    "get_delivery_statistics": ToolOperation(
        "read",
        get_delivery_statistics_tool,
        "Return parcel counts and delivery status breakdowns.",
        {
            "state": _STATE,
            "date_from": {"type": "string", "format": "date"},
            "date_to": {"type": "string", "format": "date"},
        },
    ),
    "get_pending_parcels_for_dispatch": ToolOperation(
        "read",
        get_pending_parcels_for_dispatch_tool,
        "List depot parcels ready for assignment to a driver.",
        {
            "state": _STATE,
            "max_count": {"type": "integer", "minimum": 1, "maximum": 100},
        },
    ),
    "get_available_drivers": ToolOperation(
        "read",
        get_available_drivers_tool,
        "List active drivers and their current manifest workload.",
        {"state": _STATE},
    ),
    "get_performance_metrics": ToolOperation(
        "read",
        get_performance_metrics_tool,
        "Return delivery KPIs, driver performance, and detected anomalies.",
        {
            "days_back": {"type": "integer", "minimum": 1, "maximum": 365},
            "state": _STATE,
        },
    ),
    "create_manifest": ToolOperation(
        "write",
        create_manifest_tool,
        "Create a driver manifest and assign its parcels. Requires operator approval before invocation.",
        {
            "driver_id": {"type": "string"},
            "driver_name": {"type": "string"},
            "tracking_numbers": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "maxItems": 100,
            },
            "reason": {"type": "string", "maxLength": 500},
        },
        ("driver_id", "driver_name", "tracking_numbers"),
    ),
    "update_delivery_status": ToolOperation(
        "write",
        update_delivery_status_tool,
        "Update a parcel delivery status. Requires operator approval before invocation.",
        {
            "tracking_number": {"type": "string"},
            "new_status": {
                "type": "string",
                "enum": [
                    "out_for_delivery",
                    "delivered",
                    "carded",
                    "in_transit",
                    "exception",
                    "returned",
                    "at_depot",
                ],
            },
            "location": {"type": "string"},
            "driver_note": {"type": "string", "maxLength": 1000},
        },
        ("tracking_number", "new_status", "location"),
    ),
}


def build_openapi_spec(base_url: str, access: str) -> dict[str, Any]:
    """Build the exact OpenAPI surface published in one Foundry toolbox."""
    paths: dict[str, Any] = {}
    for name, operation in TOOL_OPERATIONS.items():
        if operation.access != access:
            continue
        schema: dict[str, Any] = {
            "type": "object",
            "properties": operation.properties,
            "additionalProperties": False,
        }
        if operation.required:
            schema["required"] = list(operation.required)
        paths[f"/api/agent-tools/{access}/{name}"] = {
            "post": {
                "operationId": name,
                "description": operation.description,
                "requestBody": {
                    "required": True,
                    "content": {"application/json": {"schema": schema}},
                },
                "responses": {"200": {"description": "Tool result"}},
            }
        }

    return {
        "openapi": "3.0.3",
        "info": {
            "title": f"Zava Logistics {access.title()} Tools",
            "version": "1.0.0",
        },
        "servers": [{"url": base_url.rstrip("/")}],
        "security": [{"toolApiKey": []}],
        "components": {
            "securitySchemes": {
                "toolApiKey": {
                    "type": "apiKey",
                    "name": "x-zava-tool-key",
                    "in": "header",
                }
            }
        },
        "paths": paths,
    }


def _expected_api_key(access: str) -> str:
    setting = f"ZAVA_TOOL_{access.upper()}_API_KEY"
    return str(current_app.config.get(setting) or os.getenv(setting, ""))


@agent_tools_bp.get("/api/agent-tools/openapi/<access>.json")
def openapi_spec(access: str):
    if access not in {"read", "write"}:
        return jsonify({"error": "Unknown toolbox access level."}), 404
    return jsonify(build_openapi_spec(request.url_root, access))


@agent_tools_bp.post("/api/agent-tools/<access>/<tool_name>")
def invoke_tool(access: str, tool_name: str):
    operation = TOOL_OPERATIONS.get(tool_name)
    if operation is None or operation.access != access:
        return jsonify({"error": "Unknown tool operation."}), 404

    expected_key = _expected_api_key(access)
    supplied_key = request.headers.get("x-zava-tool-key", "")
    if not expected_key:
        return jsonify({"error": "Tool gateway is not configured."}), 503
    if not hmac.compare_digest(supplied_key, expected_key):
        return jsonify({"error": "Unauthorized."}), 401

    arguments = request.get_json(silent=True)
    if not isinstance(arguments, dict):
        return jsonify({"error": "A JSON object is required."}), 400

    missing = [name for name in operation.required if arguments.get(name) in (None, "", [])]
    if missing:
        return jsonify({"error": f"Missing required arguments: {', '.join(missing)}"}), 400

    unexpected = sorted(set(arguments) - set(operation.properties))
    if unexpected:
        return jsonify({"error": f"Unexpected arguments: {', '.join(unexpected)}"}), 400

    result = operation.function(**arguments)
    try:
        return jsonify(json.loads(result))
    except (TypeError, json.JSONDecodeError):
        return jsonify({"result": result})