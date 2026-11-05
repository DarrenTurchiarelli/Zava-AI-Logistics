"""Local-first, synthetic whole-day network planning; no operational accuracy claims.

Volumes, resources, events and priority exposure are demonstration assumptions.
Option costs are incremental illustrative costs, not quotations. Option workforce
hours are additional effort hours; facility workforce hours cover the whole day.
"""

import re
from datetime import date, datetime, time, timedelta
from math import ceil
from random import Random

from dateutil.tz import gettz

from src.domain.services.demand_planning import FACILITIES, Facility

THROUGHPUT = 120
LOAD_SIZE = 400
LABOUR_COST = 95
TRANSPORT_COST = 650
HANDLING_COST = 3
PROVENANCE = (
    "Deterministic synthetic demonstration for each centre's complete facility-local day; "
    "not operational observations, real network-scale figures or attributed real-world causes. "
    "Actual and forecast error are synthetic demonstration benchmarks, not validated accuracy. "
    "Priority/service exposure is a synthetic priority processing-capacity exposure proxy, "
    "not measured Express SLA or DIFOT. Costs are illustrative: loaded labour $95/effort-hour, "
    "transport $650/400-parcel load plus $3/parcel handling."
)


def _resources(facility: Facility) -> dict:
    rng = Random(f"network-resources:{facility.code}")
    machine = round(facility.daily_volume * rng.uniform(1.14, 1.28))
    roster = ceil(machine / THROUGHPUT)
    return {
        "machine": machine,
        "roster": roster,
        "team": ceil(roster / 8),
        "additional_hours": rng.randint(2, 5) * 8,
        "load_limit": ceil(machine * 1.25 / LOAD_SIZE) + rng.randint(2, 5),
        "transfer_limit": rng.randint(2, 5),
        "priority_pct": rng.randint(12, 25),
    }


def _events(local_day: date) -> list[dict]:
    events = []
    for period, phase, name, impact in (
        (11, 2, "Synthetic promotion pulse", 4),
        (17, 5, "Synthetic dispatch calendar pulse", 3),
    ):
        if local_day.toordinal() % period == phase:
            events.append({
                "name": name,
                "day": local_day.isoformat(),
                "impact": impact,
                "note": "Deterministic synthetic calendar assumption; not a real event or attributed cause.",
            })
    return events


def _demand(facility: Facility, local_day: date, surge: int) -> tuple[int, int]:
    weekday = (1.00, 1.02, 1.03, 1.04, 1.02, 0.91, 0.88)[local_day.weekday()]
    baseline = round(facility.daily_volume * weekday)
    rng = Random(f"network-demand:{facility.code}:{local_day.isoformat()}")
    event_pct = sum(event["impact"] for event in _events(local_day))
    forecast = round(baseline * (1 + (event_pct + rng.randint(0, 2) + surge) / 100))
    return baseline, forecast


def _capacity(resources: dict, loss: int, hours: int, labour: int = 0) -> int:
    available = 1 - loss / 100
    return max(0, int(min(
        resources["machine"] * available * (8 + hours) / 8,
        (resources["roster"] * available + resources["team"] * hours + labour) * THROUGHPUT,
        resources["load_limit"] * LOAD_SIZE,
    )))


def _exposure(constraint: int, resources: dict) -> int:
    return ceil(constraint * resources["priority_pct"] / 100)


def _facility_day(facility: Facility, local_day: date, surge: int, loss: int, hours: int) -> dict:
    resources = _resources(facility)
    baseline, forecast = _demand(facility, local_day, surge)
    capacity = _capacity(resources, loss, hours)
    constraint = max(0, forecast - capacity)
    actual = round(forecast * Random(f"network-benchmark:{facility.code}:{local_day}").uniform(0.94, 1.06))
    start = datetime.combine(local_day, time.min, tzinfo=gettz(facility.timezone))
    end = start + timedelta(days=1)
    return {
        "code": facility.code, "name": facility.name, "state": facility.state,
        "baseline": baseline, "forecast": forecast, "capacity": capacity, "constraint": constraint,
        "utilisation_pct": round(forecast / capacity * 100, 2),
        "priority_exposure": _exposure(constraint, resources),
        "variance_pct": round((forecast - baseline) / baseline * 100, 2),
        "actual": actual, "forecast_error_pct": round(abs(forecast - actual) / actual * 100, 2),
        "evidence": [
            f"Full facility-local day: {start.isoformat()} to {end.isoformat()} (exclusive).",
            "Code-seeded synthetic resources; throughput 120 parcels/effort-hour.",
            f"Synthetic daily transport reservation: {ceil(min(forecast, capacity) / LOAD_SIZE)} "
            f"loads; limit {resources['load_limit']}; transfer reservation limit {resources['transfer_limit']}.",
            "Actual/error are synthetic demonstration benchmarks, not observations or validated accuracy.",
            "Priority exposure is a synthetic processing-capacity proxy, not measured Express SLA/DIFOT.",
        ],
        "rostered_hours": resources["roster"] + resources["team"] * hours,
        "required_hours": ceil(forecast / THROUGHPUT),
        "transport_loads": ceil(min(forecast, capacity) / LOAD_SIZE),
        "spare_capacity": max(0, capacity - forecast),
    }


def _options(selected: dict, facilities: list[dict], loss: int, hours: int) -> list[dict]:
    resources = _resources(FACILITIES[selected["code"]])
    receivers = [
        row for row in facilities
        if row["state"] == selected["state"] and row["code"] != selected["code"] and row["spare_capacity"] > 0
    ]
    receivers.sort(key=lambda row: (-row["spare_capacity"], row["code"]))
    options = []
    for identifier, label, use_transfer, use_labour in (
        ("balanced-transfer", "Balanced same-state transfer", True, False),
        ("add-capacity", "Add labour / extend capacity", False, True),
        ("combined", "Combined labour and transfer", True, True),
    ):
        capacity = selected["capacity"]
        labour = extension = transferred = loads = 0
        target = None
        actions = []
        deficit = selected["constraint"]
        if use_labour and deficit:
            # Evaluate bounded resources, then buy only the smallest useful intervention.
            candidates = []
            for candidate_extension in range(3 - hours):
                for extra_labour in range(resources["additional_hours"] + 1):
                    candidate_capacity = _capacity(resources, loss, hours + candidate_extension, extra_labour)
                    effort = candidate_extension * resources["team"] + extra_labour
                    candidates.append((
                        max(0, selected["forecast"] - candidate_capacity), effort,
                        candidate_extension, extra_labour, candidate_capacity,
                    ))
            _, _, extension, labour, capacity = min(candidates)
            if capacity > selected["capacity"]:
                actions.append({
                    "type": "labour", "source_code": selected["code"],
                    "extra_staff_hours": labour, "extension_hours": extension,
                    "required_staff_hours": labour + extension * resources["team"],
                    "source_capacity_before": selected["capacity"], "source_capacity_after": capacity,
                })
            else:
                labour = extension = 0
                capacity = selected["capacity"]
        remaining = max(0, selected["forecast"] - capacity)
        if use_transfer and remaining:
            source_reserved_loads = ceil(min(selected["forecast"], capacity) / LOAD_SIZE)
            choices = []
            for receiver in receivers:
                receiver_resources = _resources(FACILITIES[receiver["code"]])
                reserved = min(
                    resources["transfer_limit"], receiver_resources["transfer_limit"],
                    resources["load_limit"] - source_reserved_loads,
                    receiver_resources["load_limit"] - receiver["transport_loads"],
                )
                amount = min(remaining, receiver["spare_capacity"], max(0, reserved) * LOAD_SIZE)
                choices.append((amount, receiver["code"], receiver))
            if choices:
                transferred, _, target = min(choices, key=lambda choice: (-choice[0], choice[1]))
            if transferred:
                loads = ceil(transferred / LOAD_SIZE)
                target_resources = _resources(FACILITIES[target["code"]])
                actions.append({
                    "type": "transfer", "source_code": selected["code"], "target_code": target["code"],
                    "parcels": transferred, "transport_loads": loads,
                    "source_forecast_before": selected["forecast"],
                    "source_forecast_after": selected["forecast"] - transferred,
                    "target_forecast_before": target["forecast"],
                    "target_forecast_after": target["forecast"] + transferred,
                    "source_capacity": capacity, "target_capacity": target["capacity"],
                    "source_reserved_loads_after": source_reserved_loads + loads,
                    "target_reserved_loads_after": target["transport_loads"] + loads,
                    "source_load_limit": resources["load_limit"],
                    "target_load_limit": target_resources["load_limit"],
                    "source_transfer_limit": resources["transfer_limit"],
                    "target_transfer_limit": target_resources["transfer_limit"],
                })
            else:
                target = None
        remaining = max(0, selected["forecast"] - transferred - capacity)
        effort = labour + extension * resources["team"]
        exposure = _exposure(remaining, resources)
        options.append({
            "id": identifier, "label": label, "viable": remaining == 0,
            "cost": effort * LABOUR_COST + loads * TRANSPORT_COST + transferred * HANDLING_COST,
            "remaining_constraint": remaining, "service_exposure": exposure,
            "required_staff_hours": effort, "transport_loads": loads,
            "target_code": target["code"] if target else None,
            "target_utilisation_pct": round(
                (target["forecast"] + transferred) / target["capacity"] * 100, 2
            ) if target else None,
            "capacity": capacity,
            "customer_impact": (
                "Synthetic processing constraint cleared; no SLA/DIFOT guarantee."
                if remaining == 0 else
                f"{remaining} parcels remain capacity-constrained; {exposure} synthetic priority parcels exposed. "
                "No SLA protection claimed."
            ),
            "actions": actions,
            "evidence": [
                "Options are independent alternatives, not cumulative reservations.",
                "Transfers conserve parcels, use one same-state receiver's actual synthetic spare, "
                "and reserve bounded loads at both ends.",
                "Additional effort is bounded by code-seeded staff availability and a two-hour extension ceiling; "
                "capacity loss continues to limit equipment even with added labour.",
                "Incremental illustrative cost: $95/effort-hour + $650/load + $3/transferred parcel.",
                "Service exposure is a synthetic priority processing-capacity proxy, not measured Express SLA/DIFOT.",
            ],
        })
    return sorted(options, key=lambda option: (not option["viable"], option["service_exposure"], option["cost"]))


def build_network_plan(
    day: str, facility_code: str = "DC-MEL-001", surge: int = 15,
    capacity_loss: int = 20, extra_hours: int = 0,
) -> dict:
    """Build a JSON-serializable synthetic full local-day plan and seven-day outlook.

    Reject noncanonical dates, unknown codes, bools/noninteger controls and values
    outside their bounds. Dates must leave room for the seven-day outlook.
    """
    if not isinstance(day, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", day):
        raise ValueError("day must be an ISO YYYY-MM-DD date.")
    try:
        local_day = date.fromisoformat(day)
        local_day + timedelta(days=6)
    except (ValueError, OverflowError) as exc:
        raise ValueError("day must be a valid ISO date with room for a seven-day outlook.") from exc
    if not isinstance(facility_code, str) or facility_code not in FACILITIES:
        raise ValueError("facility_code must identify a catalogue facility.")
    for name, value, maximum in (
        ("surge", surge, 60), ("capacity_loss", capacity_loss, 60), ("extra_hours", extra_hours, 2),
    ):
        if type(value) is not int or not 0 <= value <= maximum:
            raise ValueError(f"{name} must be a strict integer from 0 to {maximum}.")
    facilities = [
        _facility_day(
            facility, local_day, surge if code == facility_code else 0,
            capacity_loss if code == facility_code else 0, extra_hours if code == facility_code else 0,
        )
        for code, facility in FACILITIES.items()
    ]
    selected = next(row for row in facilities if row["code"] == facility_code)
    baseline = sum(row["baseline"] for row in facilities)
    forecast = sum(row["forecast"] for row in facilities)
    rollup = []
    for state in sorted({row["state"] for row in facilities}):
        rows = [row for row in facilities if row["state"] == state]
        rollup.append({
            "state": state, **{key: sum(row[key] for row in rows) for key in ("forecast", "capacity", "constraint")},
        })
    outlook = []
    for offset in range(7):
        outlook_day = local_day + timedelta(days=offset)
        demand = [
            _demand(facility, outlook_day, surge if code == facility_code else 0)
            for code, facility in FACILITIES.items()
        ]
        outlook.append({
            "day": outlook_day.isoformat(),
            "baseline": sum(values[0] for values in demand), "forecast": sum(values[1] for values in demand),
        })
    return {
        "day": day, "facility_code": facility_code,
        "inputs": {"surge": surge, "capacity_loss": capacity_loss, "extra_hours": extra_hours},
        "provenance": PROVENANCE,
        "totals": {
            "baseline": baseline, "forecast": forecast,
            "variance_pct": round((forecast - baseline) / baseline * 100, 2),
            "capacity_risks": sum(row["constraint"] > 0 for row in facilities),
            "service_risks": sum(row["priority_exposure"] > 0 for row in facilities),
        },
        "facilities": facilities, "selected": selected, "state_rollup": rollup,
        "events": _events(local_day), "outlook": outlook,
        "options": _options(selected, facilities, capacity_loss, extra_hours),
    }
