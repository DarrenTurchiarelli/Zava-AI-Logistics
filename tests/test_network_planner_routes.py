import json
import re
import sqlite3
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from itsdangerous import TimestampSigner

from src.domain.services.network_planning import build_network_plan
from src.domain.services.planning_operations import PlanningFeed, reconcile_operations
from src.infrastructure.agents.demand_planner_chat import PlannerInterpretation, PlanningTools
from src.infrastructure.database.demo_planning_store import DemoDecisionConflict, DemoPlanningStore


@pytest.fixture
def network_client(flask_app, monkeypatch, tmp_path):
    from src.interfaces.web.routes import network_planning as routes

    flask_app.config["NETWORK_DEMO_STORE_PATH"] = str(tmp_path / "demo-decisions.db")
    now = datetime(2026, 11, 6, 8, tzinfo=UTC)
    feeds = tuple(PlanningFeed(name, True, now) for name in ("parcels", "approvals", "manifests", "drivers"))
    monkeypatch.setattr(
        routes, "read_planning_operations",
        lambda code, day, **kwargs: reconcile_operations(
            code, day, {"parcels": [], "approvals": [], "manifests": [], "drivers": []}, feeds, now,
        ),
    )
    client = flask_app.test_client()
    with client.session_transaction() as session:
        session["user"] = {"username": "network-test", "role": "admin"}
        session["logged_in"] = True
    return client


def _context(response):
    assert response.status_code == 200
    return json.loads(re.search(r'<script id="network-chat-context" type="application/json">(.*?)</script>',
                               response.get_data(as_text=True), re.S).group(1))


def _plan_context(client):
    context = _context(client.get("/ai/network-demand-capacity?day=2026-11-06&surge=0&capacity_loss=0"))
    from src.interfaces.web.routes import network_planning as routes

    with client.application.test_request_context():
        plan = routes._signer().loads(context["snapshot"])
    return plan, context


def _save(client, context, option):
    return client.post("/api/network-planner/decisions", data={
        "csrf": context["csrf"], "snapshot": context["snapshot"], "action": "save",
        "option_id": option["id"], "note": "Prefer bounded response, demo only.",
    })


def test_network_hero_has_all_centres_and_explicit_provenance(network_client):
    response = network_client.get("/ai/network-demand-capacity?day=2026-11-06")
    context = _context(response)
    page = response.get_data(as_text=True)
    assert "Network Demand &amp; Capacity" in page
    assert "not measured SLA or DIFOT" in page
    assert "simulated execution only" in page
    assert "Sense → Predict → Explain" in page
    assert "Synthetic actual benchmark" in page
    assert len(context["snapshot"]) <= 24000
    from src.interfaces.web.routes import network_planning as routes

    with network_client.application.test_request_context():
        plan = routes._signer().loads(context["snapshot"])
    assert len(plan["facilities"]) == 40
    assert plan["application_context"]["eligible"] == 0
    assert len(plan["options"]) == 3


@pytest.mark.parametrize("query", ["surge=61", "capacity_loss=-1", "extra_hours=3", "surge=bad", "day=invalid", "facility=unknown", "refresh=2"])
def test_invalid_network_scenarios_are_visible(network_client, query):
    response = network_client.get("/ai/network-demand-capacity?" + query)
    assert response.status_code == 400
    assert b"valid network scenario inputs" in response.data


def test_saved_approval_and_simulated_execution_survive_new_store_instances(network_client):
    plan, context = _plan_context(network_client)
    option = next(item for item in plan["options"] if item["viable"])
    response = _save(network_client, context, option)
    assert response.status_code == 200
    saved = response.get_json()["plan"]
    assert saved["status"] == "proposed"
    payload = {"csrf": context["csrf"], "plan_id": saved["id"]}
    premature = network_client.post("/api/network-planner/decisions", data={**payload, "action": "simulate"})
    assert premature.status_code == 409
    approved = network_client.post("/api/network-planner/decisions", data={**payload, "action": "approve"})
    assert approved.get_json()["plan"]["status"] == "approved"
    simulated = network_client.post("/api/network-planner/decisions", data={**payload, "action": "simulate"})
    assert simulated.status_code == 200
    result = simulated.get_json()["plan"]
    assert result["status"] == "simulated"
    assert all(not item["operational_write"] for item in result["execution"])
    repeat = network_client.post("/api/network-planner/decisions", data={**payload, "action": "simulate"})
    assert repeat.get_json()["plan"] == result
    store = DemoPlanningStore(network_client.application.config["NETWORK_DEMO_STORE_PATH"])
    assert store.get(saved["id"]) == result
    assert [event["action"] for event in result["events"]] == ["proposed", "approved", "simulated"]
    assert b"simulated" in network_client.get("/ai/network-demand-capacity").data


def test_rejection_is_terminal_and_infeasible_plans_cannot_be_approved(tmp_path):
    store = DemoPlanningStore(str(tmp_path / "decisions.db"))
    plan = build_network_plan("2026-11-06", capacity_loss=60, surge=60)
    option = next(item for item in plan["options"] if not item["viable"])
    saved = store.save(plan, option["id"], "reviewer", "Infeasible")
    with pytest.raises(DemoDecisionConflict):
        store.transition(saved["id"], "approve", "reviewer", "")
    rejected = store.transition(saved["id"], "reject", "reviewer", "")
    assert rejected["status"] == "rejected"
    with pytest.raises(DemoDecisionConflict):
        store.transition(saved["id"], "simulate", "reviewer", "")
    assert store.get(saved["id"])["execution"] == []


def test_roles_csrf_and_snapshot_signatures_gate_demo_writes(network_client):
    plan, context = _plan_context(network_client)
    option = plan["options"][0]
    assert network_client.post("/api/network-planner/decisions", data={"action": "save"}).status_code == 403
    tampered = _save(network_client, {**context, "snapshot": context["snapshot"] + "bad"}, option)
    assert tampered.status_code == 400
    with network_client.session_transaction() as session:
        session["user"] = {"username": "network-test", "role": "customer"}
    assert _save(network_client, context, option).status_code == 403
    assert network_client.get("/ai/network-demand-capacity?preview=" + context["snapshot"]).status_code == 403


def test_non_operations_network_view_never_reads_operational_sources(network_client, monkeypatch):
    from src.interfaces.web.routes import network_planning as routes

    forbidden = MagicMock(side_effect=AssertionError("Must not read operational records"))
    monkeypatch.setattr(routes, "read_planning_operations", forbidden)
    with network_client.session_transaction() as session:
        session["user"] = {"username": "network-test", "role": "customer"}
    response = network_client.get("/ai/network-demand-capacity")
    assert response.status_code == 200
    forbidden.assert_not_called()
    assert b"Operational source context requires" in response.data
    assert b"Save proposal for review" not in response.data


def test_decision_bad_actions_note_limits_expiry_and_store_failures(network_client, monkeypatch):
    from src.interfaces.web.routes import network_planning as routes

    plan, context = _plan_context(network_client)
    assert network_client.post("/api/network-planner/decisions", data={
        "csrf": context["csrf"], "action": "dispatch",
    }).status_code == 400
    assert network_client.post("/api/network-planner/decisions", data={
        "csrf": context["csrf"], "action": "save", "note": "a" * 501,
    }).status_code == 400
    with network_client.application.app_context(), monkeypatch.context() as patch:
        patch.setattr(TimestampSigner, "get_timestamp", lambda self: 0)
        expired = routes._signer().dumps(plan)
    assert _save(network_client, {**context, "snapshot": expired}, plan["options"][0]).status_code == 400
    monkeypatch.setattr(routes, "_store", MagicMock(side_effect=sqlite3.OperationalError("unavailable")))
    failed = _save(network_client, context, plan["options"][0])
    assert failed.status_code == 503
    assert "could not save" in failed.get_json()["error"]


def test_network_agent_preview_preserves_day_facility_and_application_context(network_client, monkeypatch):
    from src.interfaces.web.routes import network_planning as routes

    plan, context = _plan_context(network_client)
    captured = {}

    def interpret(message, history, engine):
        captured.update(engine)
        return PlannerInterpretation(reply="Preview a 40% capacity loss.", changes={"capacity_loss": 40})

    monkeypatch.setattr(routes, "interpret_question", interpret)
    response = network_client.post(
        "/api/network-planner/chat", json={"snapshot": context["snapshot"], "message": "What if we lose 40% capacity?"},
        headers={"X-Planner-CSRF": context["csrf"]},
    )
    assert response.status_code == 200
    result = response.get_json()
    assert result["proposal"]["inputs"]["capacity_loss"] == 40
    assert captured["network"]["application_context"] == plan["application_context"]
    assert result["proposal"]["application_context"] == plan["application_context"]
    preview = _context(network_client.get(result["apply_url"]))
    with network_client.application.app_context():
        restored = routes._signer().loads(preview["snapshot"])
    assert restored["day"] == plan["day"]
    assert restored["facility_code"] == plan["facility_code"]
    assert restored["inputs"]["capacity_loss"] == 40


def test_network_tools_are_mode_isolated_and_calculate_without_decisions():
    plan = build_network_plan("2026-11-06")
    original = json.dumps(plan)
    tools = PlanningTools({"network": plan, "scenario": plan["inputs"]})
    assert tools.execute("get_network_snapshot", "{}") == plan
    result = tools.execute("simulate_network_scenario", '{"changes":{"capacity_loss":40,"surge":null}}')
    assert result["validated_changes"] == {"capacity_loss": 40}
    assert result["applied"] is False
    assert json.dumps(plan) == original
    assert tools.execute("compare_network_options", "{}")["options"] == plan["options"]
    from src.infrastructure.agents.demand_planner_chat import PlannerChatResponseError

    for name, arguments in [("approve", "{}"), ("simulate_scenario", '{"changes":{"transfer":800}}'),
                            ("simulate_network_scenario", '{"changes":{"capacity_loss":61}}')]:
        with pytest.raises(PlannerChatResponseError):
            tools.execute(name, arguments)


def test_network_requires_login(flask_app):
    assert flask_app.test_client().get("/ai/network-demand-capacity").status_code == 302


def test_network_registered_agent_loop_calls_tools_before_proposing_changes():
    from src.infrastructure.agents.demand_planner_chat import _run_agent

    plan = build_network_plan("2026-11-06")
    def call(name, arguments):
        item = SimpleNamespace(type="function_call", name=name, arguments=arguments, call_id=name)
        item.model_dump = lambda **kwargs: {
            "type": "function_call", "name": name, "arguments": arguments, "call_id": name,
        }
        return SimpleNamespace(status="completed", output=[item], output_text="")

    client = MagicMock()
    client.with_options.return_value = client
    client.responses.create.side_effect = [
        call("get_network_snapshot", "{}"),
        call("simulate_network_scenario", '{"changes":{"capacity_loss":40}}'),
        SimpleNamespace(status="completed", output=[], output_text='{"reply":"Preview 40% loss.","changes":{"capacity_loss":40}}'),
    ]
    result = _run_agent(client, "demand-planner", "2", "Lose 40% capacity", [], {"network": plan, "scenario": plan["inputs"]})
    assert result.changes == {"capacity_loss": 40}
    first = client.responses.create.call_args_list[0].kwargs
    assert first["tool_choice"] == {"type": "function", "name": "get_network_snapshot"}
    assert first["extra_body"] == {"agent_reference": {"type": "agent_reference", "name": "demand-planner", "version": "2"}}
    outputs = [item for item in first["input"] if item.get("type") == "function_call_output"]
    assert json.loads(outputs[1]["output"])["plan"]["inputs"]["capacity_loss"] == 40


def test_network_chat_registration_failure_is_visible_and_never_saves_decisions(network_client, monkeypatch):
    from src.infrastructure.agents.demand_planner_chat import PlannerChatUnavailable
    from src.interfaces.web.routes import network_planning as routes

    _, context = _plan_context(network_client)
    monkeypatch.setattr(routes, "interpret_question", MagicMock(side_effect=PlannerChatUnavailable("unregistered")))
    response = network_client.post(
        "/api/network-planner/chat", json={"snapshot": context["snapshot"], "message": "Compare responses"},
        headers={"X-Planner-CSRF": context["csrf"]},
    )
    assert response.status_code == 503
    assert "Register and configure" in response.get_json()["error"]
    assert DemoPlanningStore(network_client.application.config["NETWORK_DEMO_STORE_PATH"]).recent() == []


def test_network_large_decision_request_is_rejected_before_save(network_client):
    _, context = _plan_context(network_client)
    response = network_client.post("/api/network-planner/decisions", data={
        "csrf": context["csrf"], "note": "x" * 32001,
    })
    assert response.status_code == 413
