"""Deterministic parcel-facility scenarios with synthetic future demand and capacity."""

from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from math import floor
from random import Random

from dateutil.tz import gettz

from src.domain.models.distribution_centre import DISTRIBUTION_CENTRES, DistributionCentre

ARRIVAL_WEIGHTS = (0, 0, 0, 0, 0, 1, 3, 5, 10, 13, 12, 9, 7, 7, 8, 8, 6, 4, 3, 2, 1, 1, 0, 0)


@dataclass(frozen=True)
class Facility:
    code: str
    name: str
    timezone: str
    daily_volume: int
    initial_backlog: int
    state: str
    arrival_weights: tuple[int, ...] = ARRIVAL_WEIGHTS


_STATE_WORKLOAD_SCALES = {
    "NSW": (12400, 900),
    "VIC": (10800, 650),
    "QLD": (9200, 400),
    "WA": (8400, 300),
    "SA": (7600, 300),
    "ACT": (6200, 250),
    "TAS": (5400, 200),
    "NT": (4600, 150),
}


def _demo_facility(centre: DistributionCentre) -> Facility:
    # A local, code-seeded generator keeps each centre stable across requests and processes.
    generator = Random(centre.id)
    volume, backlog = _STATE_WORKLOAD_SCALES[centre.state]
    shift = generator.randint(-1, 1)
    weights = tuple(
        ARRIVAL_WEIGHTS[(hour - shift) % 24] * generator.randint(65, 145)
        for hour in range(24)
    )
    return Facility(
        code=centre.id,
        name=centre.name,
        timezone=centre.timezone,
        daily_volume=generator.randint(round(volume * 0.65), round(volume * 1.35)),
        initial_backlog=generator.randint(round(backlog * 0.5), round(backlog * 1.8)),
        state=centre.state,
        arrival_weights=weights,
    )


FACILITIES = {
    centre.id: _demo_facility(centre)
    for centre in DISTRIBUTION_CENTRES
}
HORIZONS = {"24h": "Next 24 hours", "today": "Rest of today", "7d": "Next 7 days"}
STAGES = ("Unload", "Induct / scan", "Sort", "Load / dispatch")
LIMITS = {
    "surge": (0, 60),
    "delay": (0, 4),
    "absence": (0, 50),
    "lane_outage": (0, 1),
    "extra_staff": (0, 8),
    "extra_hours": (0, 2),
    "transfer": (0, 800),
    "manual_mix": (0, 50),
    "restore_lane": (0, 1),
}

COST_LIMITS = {
    "base_team": (1, 1000),
    "base_hourly": (0, 10000),
    "extra_hourly": (0, 10000),
    "overtime_team": (1, 1000),
    "overtime_hourly": (0, 10000),
    "overhead_hourly": (0, 10000),
    "transfer_trip": (0, 1000000),
    "transfer_parcel": (0, 1000),
    "transfer_load": (1, 10000),
    "lane_restoration": (0, 1000000),
}


@dataclass(frozen=True)
class CostAssumptions:
    base_team: int = 36
    base_hourly: int = 65
    extra_hourly: int = 95
    overtime_team: int = 24
    overtime_hourly: int = 110
    overhead_hourly: int = 350
    transfer_trip: int = 650
    transfer_parcel: int = 3
    transfer_load: int = 400
    lane_restoration: int = 1500

    def __post_init__(self):
        for name, (minimum, maximum) in COST_LIMITS.items():
            value = getattr(self, name)
            if type(value) is not int or not minimum <= value <= maximum:
                raise ValueError(f"Cost assumption {name} must be a whole number from {minimum} to {maximum}.")


@dataclass(frozen=True)
class CostBreakdown:
    base_labour: int
    facility_overhead: int
    extra_labour: int
    overtime_labour: int
    transfer_transport: int
    transfer_handling: int
    lane_restoration: int
    transfer_trips: int
    base_staff_hours: int
    extra_staff_hours: int
    overtime_staff_hours: int

    @property
    def operating(self) -> int:
        return self.base_labour + self.facility_overhead

    @property
    def response(self) -> int:
        return (
            self.extra_labour + self.overtime_labour + self.transfer_transport
            + self.transfer_handling + self.lane_restoration
        )

    @property
    def total(self) -> int:
        return self.operating + self.response


@dataclass(frozen=True)
class Scenario:
    surge: int = 0
    delay: int = 0
    absence: int = 0
    lane_outage: int = 0
    extra_staff: int = 0
    extra_hours: int = 0
    transfer: int = 0
    manual_mix: int = 15
    restore_lane: int = 0

    def __post_init__(self):
        for name, (minimum, maximum) in LIMITS.items():
            value = getattr(self, name)
            if type(value) is not int or not minimum <= value <= maximum:
                raise ValueError(f"{name} must be a whole number from {minimum} to {maximum}.")


@dataclass
class Batch:
    count: int
    deadline: datetime
    missed: bool = False


@dataclass(frozen=True)
class Hour:
    label: str
    hour: int
    arrivals: int
    confirmed: int
    forecast: int
    capacity: int
    backlog: int
    dispatched: int
    cutoff: bool


@dataclass(frozen=True)
class Stage:
    name: str
    peak_queue: int
    remaining: int


@dataclass(frozen=True)
class Projection:
    hours: list[Hour]
    stages: list[Stage]
    arrivals: int
    confirmed: int
    forecast: int
    dispatched: int
    transferred: int
    deferred_arrivals: int
    peak_backlog: int
    remaining: int
    cutoff_misses: int
    cost: int
    recovery_hours: int | None
    bottleneck: str
    cost_breakdown: CostBreakdown

    @property
    def operating_cost(self) -> int:
        return self.cost_breakdown.operating

    @property
    def total_cost(self) -> int:
        return self.cost_breakdown.total


def planning_start(facility: Facility, now: datetime | None = None) -> datetime:
    local_zone = gettz(facility.timezone)
    if local_zone is None:
        raise ValueError(f"Timezone unavailable: {facility.timezone}")
    return (now or datetime.now(UTC)).astimezone(local_zone).replace(minute=0, second=0, microsecond=0)


def _deadline(arrival: datetime) -> datetime:
    earliest = arrival + timedelta(hours=4)
    for hour in (18, 22):
        candidate = arrival.replace(hour=hour)
        if candidate >= earliest:
            return candidate
    return (arrival + timedelta(days=1)).replace(hour=18)


def _capacities(at: datetime, scenario: Scenario) -> list[int]:
    if not 6 <= at.hour < 22 + scenario.extra_hours:
        return [0, 0, 0, 0]
    staff = 12 * (1 - scenario.absence / 100)
    if at.hour >= 14:
        staff += scenario.extra_staff
    # Manual items require three times the sorting effort of machine-sortable items.
    effort = 1 + 2 * scenario.manual_mix / 100
    unavailable_lanes = max(0, scenario.lane_outage - scenario.restore_lane)
    sorting = floor(min(staff * 120, (2 - unavailable_lanes) * 750) / effort)
    return [1500, 1400, sorting, 1300]


def _move(source: deque[Batch], target: deque[Batch] | None, capacity: int) -> int:
    moved = 0
    while source and moved < capacity:
        batch = source[0]
        count = min(batch.count, capacity - moved)
        if target is not None:
            target.append(Batch(count, batch.deadline, batch.missed))
        batch.count -= count
        moved += count
        if batch.count == 0:
            source.popleft()
    return moved


def _hour_at(start: datetime, offset: int) -> datetime:
    return (start.astimezone(UTC) + timedelta(hours=offset)).astimezone(start.tzinfo)


def project(
    facility: Facility,
    horizon: str,
    scenario: Scenario,
    start: datetime,
    initial_queues: tuple[int, int, int, int] | None = None,
    costs: CostAssumptions | None = None,
) -> Projection:
    if horizon not in HORIZONS:
        raise ValueError("Choose a supported planning horizon.")
    costs = costs or CostAssumptions()
    starting = initial_queues if initial_queues is not None else (0, 0, facility.initial_backlog, 0)
    if len(starting) != 4 or any(type(count) is not int or count < 0 for count in starting):
        raise ValueError("Starting queues must contain four non-negative whole parcel counts.")
    if sum(starting) != facility.initial_backlog:
        raise ValueError("Starting queues must reconcile to the facility's initial workload.")
    midnight = (start + timedelta(days=1)).replace(hour=0)
    remaining_today = round((midnight.astimezone(UTC) - start.astimezone(UTC)).total_seconds() / 3600)
    length = {"today": remaining_today, "24h": 24, "7d": 168}[horizon]
    arrivals: list[list[Batch]] = [[] for _ in range(length)]
    deferred = 0
    for index in range(length):
        at = _hour_at(start, index)
        weekday_factor = (1.0, 1.04, 1.08, 1.12, 1.2, 0.7, 0.5)[at.weekday()]
        volume = round(facility.daily_volume * weekday_factor * (1 + scenario.surge / 100))
        # Cumulative allocation avoids rounding losses across the daily profile.
        before = sum(facility.arrival_weights[: at.hour])
        total_weight = sum(facility.arrival_weights)
        count = round(volume * (before + facility.arrival_weights[at.hour]) / total_weight) - round(
            volume * before / total_weight
        )
        delayed = round(count * 0.35) if 8 <= at.hour <= 11 and scenario.delay else 0
        deadline = _deadline(at)
        if count - delayed:
            arrivals[index].append(Batch(count - delayed, deadline))
        if index + scenario.delay < length:
            if delayed:
                arrivals[index + scenario.delay].append(Batch(delayed, deadline))
        else:
            deferred += delayed

    queues: list[deque[Batch]] = [deque() for _ in STAGES]
    for index, count in enumerate(starting):
        if count:
            queues[index].append(Batch(count, _deadline(start)))
    peak_queues = list(starting)
    rows = []
    missed = dispatched = transferred = 0
    base_staff_hours = extra_staff_hours = overtime_staff_hours = 0
    transfer_budget: dict[str, int] = {}
    for index, batches in enumerate(arrivals):
        at = _hour_at(start, index)
        end = _hour_at(start, index + 1)
        count = sum(batch.count for batch in batches)
        queues[0].extend(batches)
        # Demo receiving reservations: 800/day, 400/hour; 4h transport + processing.
        if scenario.transfer and 9 <= at.hour < 15:
            day = at.date().isoformat()
            available = min(400, scenario.transfer - transfer_budget.get(day, 0))
            for batch in list(queues[0]):
                if batch.deadline >= end + timedelta(hours=4):
                    take = min(batch.count, available)
                    batch.count -= take
                    available -= take
                    transferred += take
                    transfer_budget[day] = transfer_budget.get(day, 0) + take
            queues[0] = deque(batch for batch in queues[0] if batch.count)
        caps = _capacities(at, scenario)
        for stage, queue in enumerate(queues):
            peak_queues[stage] = max(peak_queues[stage], sum(batch.count for batch in queue))
        # Reverse traversal enforces one stage per hour, rather than instant end-to-end processing.
        completed = _move(queues[3], None, caps[3])
        dispatched += completed
        for stage in (2, 1, 0):
            _move(queues[stage], queues[stage + 1], caps[stage])
        cutoff = end.hour in (18, 22)
        if cutoff:
            for queue in queues:
                for batch in queue:
                    if batch.deadline <= end and not batch.missed:
                        missed += batch.count
                        batch.missed = True
        sizes = [sum(batch.count for batch in queue) for queue in queues]
        for stage, size in enumerate(sizes):
            peak_queues[stage] = max(peak_queues[stage], size)
        if 6 <= at.hour < 22:
            base_staff_hours += costs.base_team
        if caps[0]:
            if at.hour >= 14:
                extra_staff_hours += scenario.extra_staff
            if at.hour >= 22:
                overtime_staff_hours += costs.overtime_team
        confirmed = 0
        rows.append(
            Hour(
                at.strftime("%a %d %b %H:00"),
                at.hour,
                count,
                confirmed,
                count - confirmed,
                min(caps),
                sum(sizes),
                completed,
                cutoff,
            )
        )

    remaining = sum(batch.count for queue in queues for batch in queue)
    stages = [
        Stage(name, peak_queues[index], sum(batch.count for batch in queues[index]))
        for index, name in enumerate(STAGES)
    ]
    recovery = None
    # Costing assumes transfers can consolidate into the configured load size within each local day.
    transfer_trips = sum((count + costs.transfer_load - 1) // costs.transfer_load for count in transfer_budget.values())
    breakdown = CostBreakdown(
        base_labour=base_staff_hours * costs.base_hourly,
        facility_overhead=length * costs.overhead_hourly,
        extra_labour=extra_staff_hours * costs.extra_hourly,
        overtime_labour=overtime_staff_hours * costs.overtime_hourly,
        transfer_transport=transfer_trips * costs.transfer_trip,
        transfer_handling=transferred * costs.transfer_parcel,
        lane_restoration=costs.lane_restoration if scenario.lane_outage and scenario.restore_lane else 0,
        transfer_trips=transfer_trips,
        base_staff_hours=base_staff_hours,
        extra_staff_hours=extra_staff_hours,
        overtime_staff_hours=overtime_staff_hours,
    )
    # Drain-only estimate: no further arrivals; these hours are not included in plan cost.
    for extra in range(73):
        if not any(queues):
            recovery = extra
            break
        caps = _capacities(_hour_at(start, length + extra), scenario)
        _move(queues[3], None, caps[3])
        for stage in (2, 1, 0):
            _move(queues[stage], queues[stage + 1], caps[stage])
    return Projection(
        rows,
        stages,
        sum(row.arrivals for row in rows),
        sum(row.confirmed for row in rows),
        sum(row.forecast for row in rows),
        dispatched,
        transferred,
        deferred,
        max([facility.initial_backlog] + [row.backlog for row in rows]),
        remaining,
        missed,
        breakdown.response,
        recovery,
        max(stages, key=lambda stage: stage.peak_queue).name,
        breakdown,
    )


def recommendations(baseline: Projection, scenario: Projection) -> list[str]:
    actions = []
    if scenario.cutoff_misses:
        actions.append(
            f"{scenario.cutoff_misses:,} parcels miss their modelled dispatch connection. "
            "Compare extra staff, an available second lane, and earlier arrivals before accepting this scenario."
        )
    if scenario.bottleneck == "Sort":
        actions.append(
            "Sorting is the largest queue. Compare trained afternoon staff with restoring lane availability."
        )
    else:
        actions.append(
            f"{scenario.bottleneck} has the largest queue. Extra sorting staff alone may not resolve this constraint."
        )
    difference = baseline.cutoff_misses - scenario.cutoff_misses
    actions.append(
        f"This scenario {'avoids' if difference >= 0 else 'adds'} {abs(difference):,} unique cutoff misses "
        f"versus baseline; indicative incremental cost AUD {scenario.cost:,}."
    )
    actions.append(
        "Transfers require an authorised route, available truck and receiving reservation. "
        "Held/inspection parcels are excluded; nothing is dispatched or approved by this planner."
    )
    return actions
