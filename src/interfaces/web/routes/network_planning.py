"""Network hero, explicit demo decisions and read-only agent interaction."""

import os
import secrets
import sqlite3
from datetime import timedelta
from pathlib import Path

from azure.core.exceptions import AzureError
from flask import Blueprint, abort, current_app, jsonify, render_template, request, session, url_for
from itsdangerous import BadSignature, URLSafeTimedSerializer
from openai import OpenAIError
from pydantic import TypeAdapter, ValidationError
from werkzeug.exceptions import BadRequest

from src.domain.services.demand_planning import FACILITIES, planning_start
from src.domain.services.network_planning import build_network_plan
from src.domain.services.planning_operations import PlanningOperations
from src.infrastructure.agents.demand_planner_chat import (
    ChatMessage,
    PlannerChatResponseError,
    PlannerChatUnavailable,
    interpret_question,
)
from src.infrastructure.database.demo_planning_store import DemoDecisionConflict, DemoPlanningStore
from src.infrastructure.database.planning_source import read_planning_operations
from src.interfaces.web.middleware import login_required

network_bp = Blueprint("network_planner", __name__)


def _role():
    if session.get("user", {}).get("role") not in {"admin", "depot_manager"}:
        abort(403, description="Network demo decisions require an admin or depot manager role.")


def _signer():
    return URLSafeTimedSerializer(current_app.secret_key, salt="network-demo-plan-v1")


def _store():
    default = Path("/home/data/network-demo-plans.db") if os.getenv("WEBSITE_SITE_NAME") else Path(current_app.instance_path) / "network-demo-plans.db"
    return DemoPlanningStore(current_app.config.get("NETWORK_DEMO_STORE_PATH", str(default)))


def _csrf():
    expected = session.get("network_planner_csrf", "")
    supplied = request.form.get("csrf", "") or request.headers.get("X-Planner-CSRF", "")
    if not expected or not secrets.compare_digest(expected.encode(), supplied.encode()):
        abort(403, description="Reload the network planner before making a decision.")


def _token_plan(token):
    if not isinstance(token, str) or len(token) > 24000:
        raise ValueError("Invalid network plan snapshot.")
    plan = _signer().loads(token, max_age=1800)
    if not isinstance(plan, dict):
        raise ValueError("Invalid network plan snapshot.")
    if plan.get("application_context") and session.get("user", {}).get("role") not in {"admin", "depot_manager"}:
        abort(403, description="Application planning snapshots require an admin or depot manager role.")
    return plan


@network_bp.route("/ai/network-demand-capacity")
@login_required
def index():
    facility = request.args.get("facility", "DC-MEL-001")
    try:
        if facility not in FACILITIES:
            raise ValueError("Choose a supported centre.")
        local_day = planning_start(FACILITIES[facility]).date()
        day = request.args.get("day", (local_day + timedelta(days=1)).isoformat())
        if request.args.get("preview"):
            plan = _token_plan(request.args["preview"])
        else:
            plan = build_network_plan(
                day, facility, int(request.args.get("surge", "15")),
                int(request.args.get("capacity_loss", "20")), int(request.args.get("extra_hours", "0")),
            )
        operations = None
        if session.get("user", {}).get("role") in {"admin", "depot_manager"}:
            refresh = request.args.get("refresh", "0")
            if refresh not in {"0", "1"}:
                raise ValueError("Refresh must be 0 or 1.")
            if not request.args.get("preview"):
                operations = read_planning_operations(
                    plan["facility_code"], planning_start(FACILITIES[plan["facility_code"]]).date().isoformat(),
                    **({"refresh": True} if refresh == "1" else {}),
                )
                plan["application_context"] = TypeAdapter(PlanningOperations).dump_python(operations, mode="json")
        recent = _store().recent() if session.get("user", {}).get("role") in {"admin", "depot_manager"} else []
    except (ValueError, BadSignature) as exc:
        current_app.logger.warning("Invalid network planning request: %s", exc)
        return render_template("network_demand_planning.html", error="Choose valid network scenario inputs, or reload an expired preview."), 400
    except (sqlite3.Error, OSError):
        current_app.logger.exception("Network demo decision store could not be read")
        return render_template("network_demand_planning.html", error="The separate demo decision store is unavailable."), 503
    csrf = session.setdefault("network_planner_csrf", secrets.token_urlsafe(32))
    return render_template(
        "network_demand_planning.html", plan=plan, operations=plan.get("application_context"), recent=recent,
        snapshot=_signer().dumps(plan), csrf=csrf, can_decide=session.get("user", {}).get("role") in {"admin", "depot_manager"},
    )


@network_bp.route("/api/network-planner/decisions", methods=["POST"])
@login_required
def decisions():
    _role()
    if request.content_length and request.content_length > 32000:
        return jsonify(error="The demo decision request is too large."), 413
    _csrf()
    action = request.form.get("action", "")
    note = request.form.get("note", "").strip()
    if len(note) > 500:
        return jsonify(error="Use a decision note of at most 500 characters."), 400
    try:
        store = _store()
        actor = session["user"].get("username", "demo-planner")
        if action == "save":
            plan = store.save(_token_plan(request.form.get("snapshot")), request.form.get("option_id", ""), actor, note)
        else:
            plan = store.transition(request.form.get("plan_id", ""), action, actor, note)
    except KeyError:
        return jsonify(error="Demo plan not found."), 404
    except DemoDecisionConflict as exc:
        return jsonify(error=str(exc)), 409
    except (ValueError, BadSignature) as exc:
        current_app.logger.warning("Invalid network demo decision: %s", exc)
        return jsonify(error="Invalid option, action or expired snapshot. Reload the planner."), 400
    except (sqlite3.Error, OSError):
        current_app.logger.exception("Network demo decision could not be saved")
        return jsonify(error="The demo decision store could not save the action; retry without assuming success."), 503
    return jsonify(plan=plan, message="Demo record saved. No parcel, roster or transport system was changed.")


@network_bp.route("/api/network-planner/chat", methods=["POST"])
@login_required
def chat():
    _csrf()
    if not request.is_json or (request.content_length and request.content_length > 32000):
        return jsonify(error="Send a bounded JSON network planning question."), 400
    try:
        data = request.get_json()
    except BadRequest:
        return jsonify(error="Send valid JSON for the network question."), 400
    if not isinstance(data, dict) or set(data) - {"snapshot", "message"}:
        return jsonify(error="Send a snapshot and planning question."), 400
    try:
        question = ChatMessage(role="user", content=data.get("message", ""))
        if len(question.content) > 2000 or not question.content.strip():
            raise ValueError("Enter a meaningful question of up to 2,000 characters.")
        plan = _token_plan(data.get("snapshot"))
        result = interpret_question(question.content, [], {"network": plan, "scenario": plan["inputs"]})
    except (ValueError, BadSignature, ValidationError):
        return jsonify(error="Invalid question or expired network context. Reload the planner."), 400
    except (PlannerChatUnavailable, AzureError, OpenAIError):
        current_app.logger.exception("Dedicated network planning agent is unavailable")
        return jsonify(error="Register and configure the dedicated Foundry agent before using network chat. Manual scenarios and demo decisions still work."), 503
    except PlannerChatResponseError:
        current_app.logger.exception("Invalid dedicated network agent response")
        return jsonify(error="The agent response could not be validated; no plan or decision was changed."), 502
    proposed = None
    apply_url = None
    if result.changes:
        values = {**plan["inputs"], **result.changes}
        proposed = build_network_plan(plan["day"], plan["facility_code"], **values)
        if "application_context" in plan:
            proposed["application_context"] = plan["application_context"]
        apply_url = url_for("network_planner.index", preview=_signer().dumps(proposed))
    return jsonify(reply=result.reply, changes=result.changes, proposal=proposed, apply_url=apply_url)
