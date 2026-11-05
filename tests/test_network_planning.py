import json
import os
import subprocess
from datetime import date, timedelta

import pytest

from src.domain.services.demand_planning import FACILITIES
from src.domain.services.network_planning import _resources, build_network_plan

DAY = "2026-11-06"


def test_catalogue_schema_and_rollups():
    plan = build_network_plan(DAY)
    assert len(plan["facilities"]) == len(FACILITIES) == 40
    assert {row["code"] for row in plan["facilities"]} == set(FACILITIES)
    assert plan["selected"]["code"] == plan["facility_code"] == "DC-MEL-001"
    assert set(plan) == {
        "day", "facility_code", "inputs", "provenance", "totals", "facilities",
        "selected", "state_rollup", "events", "outlook", "options",
    }
    assert set(plan["selected"]) == {
        "code", "name", "state", "baseline", "forecast", "capacity", "constraint",
        "utilisation_pct", "priority_exposure", "variance_pct", "actual", "forecast_error_pct",
        "evidence", "rostered_hours", "required_hours", "transport_loads", "spare_capacity",
    }
    assert set(plan["totals"]) == {"baseline", "forecast", "variance_pct", "capacity_risks", "service_risks"}
    for key in ("forecast", "baseline"):
        assert plan["totals"][key] == sum(row[key] for row in plan["facilities"])
    assert plan["totals"]["capacity_risks"] == sum(row["constraint"] > 0 for row in plan["facilities"])
    assert plan["totals"]["service_risks"] == sum(row["priority_exposure"] > 0 for row in plan["facilities"])
    for state in plan["state_rollup"]:
        rows = [row for row in plan["facilities"] if row["state"] == state["state"]]
        for key in ("forecast", "capacity", "constraint"):
            assert state[key] == sum(row[key] for row in rows)
    assert len(plan["outlook"]) == 7
    assert plan["outlook"][0] == {
        "day": DAY, "baseline": plan["totals"]["baseline"], "forecast": plan["totals"]["forecast"],
    }
    assert [row["day"] for row in plan["outlook"]] == [
        (date.fromisoformat(DAY) + timedelta(days=offset)).isoformat() for offset in range(7)
    ]
    assert "not validated accuracy" in plan["provenance"]
    assert "not measured Express SLA or DIFOT" in plan["provenance"]
    assert json.loads(json.dumps(plan, allow_nan=False)) == plan


def test_deterministic_across_processes_and_hash_seeds():
    expected = json.dumps(build_network_plan(DAY), sort_keys=True)
    import sys

    for seed in ("1", "222"):
        result = subprocess.run(
            [sys.executable, "-c",
             f"import json; from src.domain.services.network_planning import build_network_plan; "
             f"print(json.dumps(build_network_plan('{DAY}'), sort_keys=True))"],
            capture_output=True, text=True, check=True, env={**os.environ, "PYTHONHASHSEED": seed},
        )
        assert result.stdout.strip() == expected
    plan = build_network_plan(DAY)
    plan["selected"]["forecast"] = 0
    assert json.dumps(build_network_plan(DAY), sort_keys=True) == expected


@pytest.mark.parametrize("day", [
    None, 20261106, "", "2026-1-01", "20261106", "2026-11-06T00:00:00",
    "2026-02-29", "2026-13-01", "0000-01-01", "2026-11-06 ", "9999-12-26",
])
def test_reject_invalid_dates(day):
    with pytest.raises(ValueError):
        build_network_plan(day)


@pytest.mark.parametrize("code", [None, [], 1, "", "DC-NOT-001", "dc-mel-001"])
def test_reject_invalid_codes(code):
    with pytest.raises(ValueError):
        build_network_plan(DAY, code)


@pytest.mark.parametrize("name,maximum", [("surge", 60), ("capacity_loss", 60), ("extra_hours", 2)])
@pytest.mark.parametrize("value", [-1, True, False, None, "1", 1.0, [], float("nan"), float("inf")])
def test_strict_controls(name, maximum, value):
    with pytest.raises(ValueError):
        build_network_plan(DAY, **{name: value})
    with pytest.raises(ValueError):
        build_network_plan(DAY, **{name: maximum + 1})


@pytest.mark.parametrize("code", list(FACILITIES))
def test_all_centres_zero_and_positive_constraints(code):
    clear = build_network_plan(DAY, code, surge=0, capacity_loss=0)
    assert all(row["constraint"] == 0 for row in clear["facilities"])
    assert all(option["viable"] and option["cost"] == 0 and not option["actions"] for option in clear["options"])
    stressed = build_network_plan(DAY, code)
    assert stressed["selected"]["constraint"] > 0
    assert any(option["actions"] for option in stressed["options"])


def test_controls_affect_only_selected_facility_and_thresholds():
    clear = build_network_plan(DAY, surge=0, capacity_loss=0)
    stressed = build_network_plan(DAY, surge=60, capacity_loss=60, extra_hours=2)
    assert clear["selected"]["baseline"] == stressed["selected"]["baseline"]
    for before, after in zip(clear["facilities"], stressed["facilities"], strict=True):
        if before["code"] != clear["facility_code"]:
            assert before == after
    assert stressed["selected"]["forecast"] > clear["selected"]["forecast"]
    assert stressed["selected"]["capacity"] < clear["selected"]["capacity"]
    assert build_network_plan(DAY, extra_hours=2)["selected"]["capacity"] >= build_network_plan(DAY)["selected"]["capacity"]


@pytest.mark.parametrize("code", list(FACILITIES))
@pytest.mark.parametrize("surge,loss,hours", [(15, 20, 0), (60, 60, 2), (0, 0, 2)])
def test_option_resource_conservation_and_nonnegative_amounts(code, surge, loss, hours):
    plan = build_network_plan(DAY, code, surge, loss, hours)
    selected = plan["selected"]
    facilities = {row["code"]: row for row in plan["facilities"]}
    options = plan["options"]
    assert len(options) == 3
    assert {option["id"] for option in options} == {"balanced-transfer", "add-capacity", "combined"}
    assert options == sorted(options, key=lambda row: (not row["viable"], row["service_exposure"], row["cost"]))
    for option in options:
        assert set(option) == {
            "id", "label", "viable", "cost", "remaining_constraint", "service_exposure",
            "required_staff_hours", "transport_loads", "target_code", "target_utilisation_pct",
            "capacity", "customer_impact", "actions", "evidence",
        }
        transfers = [action for action in option["actions"] if action["type"] == "transfer"]
        transferred = sum(action["parcels"] for action in transfers)
        assert option["remaining_constraint"] == max(0, selected["forecast"] - transferred - option["capacity"])
        assert option["viable"] is (option["remaining_constraint"] == 0)
        assert option["service_exposure"] <= option["remaining_constraint"]
        assert option["capacity"] >= selected["capacity"]
        assert option["cost"] == (
            option["required_staff_hours"] * 95 + option["transport_loads"] * 650 + transferred * 3
        )
        for action in transfers:
            receiver = facilities[action["target_code"]]
            assert receiver["state"] == selected["state"]
            assert receiver["code"] != selected["code"]
            assert action["parcels"] <= receiver["spare_capacity"]
            assert action["source_forecast_before"] + action["target_forecast_before"] == (
                action["source_forecast_after"] + action["target_forecast_after"]
            )
            assert action["target_forecast_after"] <= action["target_capacity"] == receiver["capacity"]
            assert action["parcels"] <= action["transport_loads"] * 400
            assert (action["transport_loads"] - 1) * 400 < action["parcels"]
            for end in ("source", "target"):
                assert action[f"{end}_reserved_loads_after"] <= action[f"{end}_load_limit"]
                assert action["transport_loads"] <= action[f"{end}_transfer_limit"]
            assert action["source_reserved_loads_after"] >= (
                (min(action["source_forecast_after"], option["capacity"]) + 399) // 400
                + action["transport_loads"]
            )
            assert action["target_reserved_loads_after"] == receiver["transport_loads"] + action["transport_loads"]
            assert option["target_utilisation_pct"] <= 100
        if not transfers:
            assert option["target_code"] is None
            assert option["target_utilisation_pct"] is None
        for action in option["actions"]:
            if action["type"] == "labour":
                resources = _resources(FACILITIES[code])
                assert action["extra_staff_hours"] <= resources["additional_hours"]
                assert action["extension_hours"] + hours <= 2
                assert option["capacity"] <= int(resources["machine"] * (1 - loss / 100) * 1.25)
        if not option["viable"]:
            assert "No SLA protection claimed" in option["customer_impact"]

    def assert_nonnegative(value):
        if isinstance(value, dict):
            for child in value.values():
                assert_nonnegative(child)
        elif isinstance(value, list):
            for child in value:
                assert_nonnegative(child)
        elif isinstance(value, (int, float)):
            assert value >= 0

    assert_nonnegative(plan)
    json.dumps(plan, allow_nan=False)
    for row in plan["facilities"]:
        assert row["constraint"] == max(0, row["forecast"] - row["capacity"])
        assert row["spare_capacity"] == max(0, row["capacity"] - row["forecast"])
        assert row["required_hours"] == (row["forecast"] + 119) // 120
        assert row["actual"] > 0
        assert row["forecast_error_pct"] == round(abs(row["forecast"] - row["actual"]) / row["actual"] * 100, 2)


@pytest.mark.parametrize("code", list(FACILITIES))
def test_high_loss_cannot_invent_safe_option(code):
    plan = build_network_plan(DAY, code, surge=60, capacity_loss=60, extra_hours=2)
    assert all(not option["viable"] and option["remaining_constraint"] > 0 for option in plan["options"])


def test_calendar_variation_and_full_local_day():
    plans = [build_network_plan((date(2026, 10, 1) + timedelta(days=i)).isoformat()) for i in range(31)]
    events = [event for plan in plans for event in plan["events"]]
    assert events
    assert all("not a real event" in event["note"] for event in events)
    assert all(event["day"] == plan["day"] for plan in plans for event in plan["events"])
    melbourne = build_network_plan("2026-10-04")["selected"]
    assert "2026-10-04T00:00:00+10:00 to 2026-10-05T00:00:00+11:00" in melbourne["evidence"][0]
    assert build_network_plan("2024-02-29")["day"] == "2024-02-29"
    assert build_network_plan("9999-12-25")["outlook"][-1]["day"] == "9999-12-31"


def test_calendar_pulses_do_not_create_pointless_zero_control_spend():
    for offset in range(187):
        day = (date(2026, 1, 1) + timedelta(days=offset)).isoformat()
        plan = build_network_plan(day, surge=0, capacity_loss=0)
        assert all(row["constraint"] == 0 for row in plan["facilities"])
        assert all(option["viable"] and option["cost"] == 0 for option in plan["options"])


def test_default_demo_has_real_transfers_and_viable_and_infeasible_choices():
    plan = build_network_plan(DAY)
    assert any(option["viable"] for option in plan["options"])
    assert any(not option["viable"] for option in plan["options"])
    assert any(action["type"] == "transfer" for option in plan["options"] for action in option["actions"])
