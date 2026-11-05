"""Reconcile application records into anonymous, read-only planning inputs."""

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from src.domain.models.distribution_centre import DISTRIBUTION_CENTRES


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _normalise(value: object) -> str:
    return re.sub(r"[\s-]+", "_", _text(value).lower())


def _location_key(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", _text(value).lower())


_CENTRE_ALIASES = {
    _location_key(value): centre.id
    for centre in DISTRIBUTION_CENTRES
    for value in (centre.id, centre.name, f"{centre.id} - {centre.name}")
}
_CENTRE_STATES = {centre.id: centre.state for centre in DISTRIBUTION_CENTRES}
_TERMINAL = {"delivered", "returned", "cancelled", "canceled"}
_OUTBOUND = {"in_transit", "out_for_delivery"}
_HELD = {"held", "on_hold", "pending", "pending_approval", "awaiting_approval", "inspection"}
_PRE_ARRIVAL = {"registered", "collected"}
_STAGES = {"at_depot": 0, "sorting": 2}


@dataclass(frozen=True)
class PlanningFeed:
    name: str
    available: bool
    fetched_at: datetime
    records: int | None = None
    latest_update: datetime | None = None
    issue: str | None = None


@dataclass(frozen=True)
class PlanningOperations:
    facility_code: str
    fetched_at: datetime
    feeds: tuple[PlanningFeed, ...] = ()
    initial_queues: tuple[int, int, int, int] | None = None
    eligible: int | None = None
    held: int | None = None
    awaiting_review: int | None = None
    pending_requests: int | None = None
    pending_parcels: int | None = None
    outbound: int | None = None
    pre_arrival: int | None = None
    unknown_status: int | None = None
    unmapped_parcels: int | None = None
    duplicate_parcels: int = 0
    active_manifests: int | None = None
    manifest_parcels: int | None = None
    assigned_drivers: int | None = None
    state_driver_accounts: int | None = None
    unlocated_driver_accounts: int | None = None
    stale_manifests: int | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def connected(self) -> bool:
        return self.initial_queues is not None


def resolve_centre(location: object) -> str | None:
    return _CENTRE_ALIASES.get(_location_key(location))


def _identifiers(record: dict[str, Any], fields: tuple[str, ...]) -> set[str]:
    return {value for name in fields if (value := _text(record.get(name)))}


def _timestamp(value: object) -> float:
    return float(value) if type(value) in (int, float) else 0


def latest_record_update(records: list[dict[str, Any]]) -> datetime | None:
    timestamps = [_timestamp(record.get("_ts")) for record in records]
    latest = max(timestamps, default=0)
    return datetime.fromtimestamp(latest, UTC) if latest > 0 else None


def _unique_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique = {}
    for index, record in enumerate(records):
        key = _text(record.get("id")) or f"missing-id-{index}"
        previous = unique.get(key)
        if previous is None or _timestamp(record.get("_ts")) >= _timestamp(previous.get("_ts")):
            unique[key] = record
    return list(unique.values())


def reconcile_operations(
    facility_code: str,
    local_day: str,
    records: dict[str, list[dict[str, Any]] | None],
    feeds: tuple[PlanningFeed, ...],
    fetched_at: datetime,
) -> PlanningOperations:
    warnings = [feed.issue for feed in feeds if feed.issue]
    for feed in feeds:
        if feed.latest_update and fetched_at - feed.latest_update > timedelta(days=1):
            warnings.append(f"{feed.name}: latest stored update is over 24 hours old; this is not a fresh scan feed.")
    parcels = records.get("parcels")
    approvals = records.get("approvals")
    manifests = records.get("manifests")
    drivers = records.get("drivers")
    values: dict[str, Any] = {}

    unique_parcels: list[dict[str, Any]] = []
    aliases: dict[str, int] = {}
    ambiguous: set[str] = set()
    if parcels is not None:
        # Connect barcode/tracking aliases before deduplicating, including transitive duplicates.
        groups: list[list[dict[str, Any]]] = []
        for parcel in parcels:
            identifiers = _identifiers(parcel, ("id", "barcode", "tracking_number"))
            matches = {aliases[key] for key in identifiers if key in aliases}
            target = min(matches) if matches else len(groups)
            if not matches:
                groups.append([])
            for other in matches - {target}:
                groups[target].extend(groups[other])
                groups[other] = []
                aliases = {key: target if group == other else group for key, group in aliases.items()}
            groups[target].append(parcel)
            for key in identifiers:
                aliases[key] = target
        aliases = {}
        for group in groups:
            if not group:
                continue
            latest = max(group, key=lambda record: _timestamp(record.get("_ts")))
            locations = {resolve_centre(record.get("current_location")) for record in group}
            locations.discard(None)
            if len(locations) > 1:
                ambiguous.update(
                    key for record in group for key in _identifiers(record, ("id", "barcode", "tracking_number"))
                )
            index = len(unique_parcels)
            unique_parcels.append(latest)
            for record in group:
                for key in _identifiers(record, ("id", "barcode", "tracking_number")):
                    aliases[key] = index
        values["duplicate_parcels"] = len(parcels) - len(unique_parcels)
        if values["duplicate_parcels"]:
            warnings.append(f"{values['duplicate_parcels']} duplicate parcel records were reconciled by identifier.")
        if ambiguous:
            warnings.append("Duplicate parcel identifiers have conflicting centre locations; affected parcels are excluded.")

    pending: dict[int, set[str]] = {}
    unmatched_requests = 0
    if approvals is not None:
        centre_requests: set[str] = set()
        centre_pending: set[int] = set()
        for index, approval in enumerate(_unique_records(approvals)):
            if _normalise(approval.get("status")) != "pending":
                continue
            matches = {
                aliases[key] for key in _identifiers(
                    approval, ("parcel_barcode", "barcode", "tracking_number", "parcel_id")
                ) if key in aliases and key not in ambiguous
            }
            if len(matches) != 1:
                unmatched_requests += 1
                continue
            parcel_index = next(iter(matches))
            request_id = _text(approval.get("id")) or f"request-{index}"
            pending.setdefault(parcel_index, set()).add(request_id)
            if resolve_centre(unique_parcels[parcel_index].get("current_location")) == facility_code:
                centre_requests.add(request_id)
                centre_pending.add(parcel_index)
        if parcels is not None:
            values.update(pending_requests=len(centre_requests), pending_parcels=len(centre_pending))
        if unmatched_requests:
            warnings.append(f"{unmatched_requests} pending approval requests could not be linked uniquely to a parcel.")

    centre_indices: set[int] = set()
    if parcels is not None:
        queues = [0, 0, 0, 0]
        held = awaiting_review = outbound = pre_arrival = unknown = unmapped = 0
        missing_identity = 0
        for index, parcel in enumerate(unique_parcels):
            identifiers = _identifiers(parcel, ("id", "barcode", "tracking_number"))
            location = resolve_centre(parcel.get("current_location"))
            if not location or identifiers & ambiguous or not identifiers:
                unmapped += 1
                missing_identity += not bool(identifiers)
                continue
            if location != facility_code:
                continue
            centre_indices.add(index)
            status = _normalise(parcel.get("current_status"))
            if parcel.get("is_delivered") is True or status in _TERMINAL:
                continue
            if status in _OUTBOUND:
                outbound += 1
            elif status in _HELD or (
                parcel.get("requires_approval") is True
                and _normalise(parcel.get("approval_status")) not in {"approved", "auto_approved"}
            ):
                held += 1
            elif status in _STAGES:
                if index in pending:
                    awaiting_review += 1
                else:
                    queues[_STAGES[status]] += 1
            elif status in _PRE_ARRIVAL:
                pre_arrival += 1
            else:
                unknown += 1
        values.update(
            eligible=sum(queues) if approvals is not None else None,
            held=held, awaiting_review=awaiting_review if approvals is not None else None,
            outbound=outbound, pre_arrival=pre_arrival, unknown_status=unknown, unmapped_parcels=unmapped,
        )
        if approvals is not None:
            values["initial_queues"] = tuple(queues)
        if unmapped:
            warnings.append(
                f"{unmapped} network parcel records lack an unambiguous current centre/identity and are excluded. "
                "Lodgement location, destination and state are not used to invent current location."
            )
        if missing_identity:
            warnings.append(f"{missing_identity} parcel records have no usable identifier.")
        if unknown:
            warnings.append(f"{unknown} centre parcels have unsupported processing statuses and are excluded.")
        if awaiting_review:
            warnings.append(
                f"{awaiting_review} otherwise-processable parcels have pending approval links. "
                "Their release eligibility is unknown; they are conservatively excluded, not asserted to be physical holds."
            )
    if parcels is None or approvals is None:
        warnings.append(
            "Application starting workload is not used because the parcel or approval feed is unavailable. "
            "The projection uses an explicitly synthetic starting backlog instead; unavailable counts are not zero."
        )

    if manifests is not None:
        active = []
        stale = 0
        for manifest in _unique_records(manifests):
            if _normalise(manifest.get("status")) not in {"active", "in_progress"}:
                continue
            if manifest.get("manifest_date") != local_day:
                stale += 1
                continue
            active.append(manifest)
        values["stale_manifests"] = stale
        if stale:
            warnings.append(f"{stale} active network manifests are not dated {local_day} and are excluded from today's context.")
        if parcels is not None:
            linked_manifests: set[str] = set()
            linked_parcels: set[int] = set()
            linked_drivers: set[str] = set()
            unresolved_items = 0
            for manifest in active:
                items = manifest.get("items")
                if not isinstance(items, list):
                    warnings.append("A current active manifest has no valid item list; it cannot be linked to a centre.")
                    continue
                matched = set()
                for item in items:
                    if not isinstance(item, dict):
                        unresolved_items += 1
                        continue
                    links = {
                        aliases[key] for key in _identifiers(item, ("barcode", "tracking_number"))
                        if key in aliases and key not in ambiguous
                    }
                    if len(links) != 1:
                        unresolved_items += 1
                        continue
                    index = next(iter(links))
                    if index in centre_indices:
                        matched.add(index)
                if matched:
                    linked_manifests.add(_text(manifest.get("id")))
                    linked_parcels.update(matched)
                    if driver := _text(manifest.get("driver_id")):
                        linked_drivers.add(driver)
            values.update(
                active_manifests=len(linked_manifests), manifest_parcels=len(linked_parcels),
                assigned_drivers=len(linked_drivers),
            )
            if unresolved_items:
                warnings.append(
                    f"{unresolved_items} current manifest item references do not identify a unique parcel; "
                    "they are excluded from centre-linked outbound totals."
                )
    if drivers is not None:
        state = _CENTRE_STATES[facility_code]
        directory = _unique_records(drivers)
        values["state_driver_accounts"] = sum(
            driver.get("active") is True and driver.get("state") == state for driver in directory
        )
        values["unlocated_driver_accounts"] = sum(
            driver.get("active") is True and not _text(driver.get("state")) for driver in directory
        )
        if values["unlocated_driver_accounts"]:
            warnings.append(
                f"{values['unlocated_driver_accounts']} active driver accounts have no state assignment. "
                "Driver accounts and delivery assignments are not a live availability roster or sorting capacity."
            )
    return PlanningOperations(
        facility_code=facility_code, fetched_at=fetched_at, feeds=feeds,
        warnings=tuple(warnings), **values,
    )
