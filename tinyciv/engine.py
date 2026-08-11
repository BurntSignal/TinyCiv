from __future__ import annotations

import hashlib
import json
import math
import os
import random
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

YEAR_SECONDS = int(os.getenv("TINYCIV_YEAR_SECONDS", "3600"))
DATA_DIR = Path(os.getenv("TINYCIV_DATA_DIR", "/data"))
STATE_PATH = DATA_DIR / "tinyciv_state.json"
WORLD_SCHEMA = 4

SETTLEMENT_NAMES = [
    "Mossvale", "Brasswick", "Fernhollow", "Emberford", "Tinkerfen",
    "Rookhaven", "Thistlebarrow", "Coppermere", "Lanternreach", "Oakrest",
    "Wrenfield", "Stonewillow", "Alderwick", "Cinderbrook", "Dunmere",
    "Foxglove", "Marrowfen", "Pinewatch", "Rainbarrow", "Westmere",
]

FOUNDING_TITLES = [
    "Compact", "Commonwealth", "Hearth", "Settlement", "Freehold", "Union",
]

GIVEN_NAMES = [
    "Alden", "Anwen", "Bram", "Cora", "Dessa", "Elian", "Fenn", "Galen",
    "Hesta", "Iven", "Junia", "Kellan", "Liora", "Marek", "Nessa", "Orin",
    "Pella", "Quill", "Rhea", "Soren", "Tamsin", "Ulric", "Veda", "Wren",
    "Yara", "Zev", "Mira", "Tobin", "Edda", "Rowan", "Iris", "Calder",
]

SURNAMES = [
    "Ash", "Barrow", "Bell", "Briar", "Cairn", "Dale", "Ember", "Fallow",
    "Finch", "Flint", "Grove", "Hale", "Hearth", "Kestrel", "Lark", "Moss",
    "Pike", "Reed", "Rook", "Rowe", "Stone", "Thorn", "Vale", "Wick",
]

CULTURE_TRAITS = [
    "patient", "restless", "communal", "practical", "ceremonial", "curious",
    "stoic", "competitive", "hospitable", "frugal", "inventive", "traditional",
]

DISCOVERIES = [
    ("crop rotation", 12),
    ("kiln-fired brick", 18),
    ("water-driven milling", 24),
    ("formal surveying", 31),
    ("movable type", 39),
    ("precision gearing", 48),
    ("mechanical pumping", 56),
    ("standardized measures", 64),
    ("optical glass", 72),
    ("steam pressure", 82),
    ("electrical induction", 91),
]

INSTITUTIONS = [
    ("a public granary", 18, 25),
    ("an infirmary", 24, 28),
    ("a record hall", 30, 32),
    ("a schoolhouse", 38, 36),
    ("a market council", 55, 40),
    ("a survey office", 75, 46),
    ("a civic court", 110, 50),
    ("an academy", 180, 58),
    ("a public works office", 260, 64),
]

POPULATION_MILESTONES = [25, 50, 100, 250, 500, 1000, 2500, 5000, 10000, 25000, 50000, 100000]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def parse_iso(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def clamp(value: float, low: float = 0, high: float = 100) -> float:
    return max(low, min(high, value))


def stable_seed(value: str) -> int:
    digest = hashlib.sha256(value.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


class TinyCivEngine:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.state = self._load_or_create()

    def _person_name(self, rng: random.Random | None = None) -> str:
        rng = rng or random
        return f"{rng.choice(GIVEN_NAMES)} {rng.choice(SURNAMES)}"

    def _root_settlement_name(self, civ_name: str) -> str:
        return civ_name.split()[0] if civ_name else random.choice(SETTLEMENT_NAMES)

    def _era(self, state: dict[str, Any]) -> str:
        pop = state["population"]
        knowledge = state["knowledge"]
        if pop >= 1200 and knowledge >= 82:
            return "Machine Age"
        if pop >= 550 and knowledge >= 62:
            return "Civic Age"
        if pop >= 220 and knowledge >= 42:
            return "Town Age"
        if pop >= 80 and knowledge >= 25:
            return "Village Age"
        return "Hearth Age"

    def _new_state(self) -> dict[str, Any]:
        now = utc_now()
        settlement = random.choice(SETTLEMENT_NAMES)
        title = random.choice(FOUNDING_TITLES)
        world_id = str(uuid.uuid4())
        rng = random.Random(stable_seed(world_id))
        population = random.randint(11, 17)
        state: dict[str, Any] = {
            "schema_version": WORLD_SCHEMA,
            "world_id": world_id,
            "world_seed": rng.randrange(1, 2**63),
            "name": f"{settlement} {title}",
            "status": "living",
            "founded_at": iso(now),
            "last_simulated_at": iso(now),
            "last_visit_at": None,
            "last_visit_year": 0,
            "last_visit_snapshot": None,
            "year": 1,
            "population": population,
            "population_peak": population,
            "food": random.randint(62, 78),
            "health": random.randint(68, 82),
            "morale": random.randint(60, 78),
            "knowledge": random.randint(5, 12),
            "stability": random.randint(65, 82),
            "last_era": "Hearth Age",
            "society": {
                "traits": rng.sample(CULTURE_TRAITS, 2),
                "cohesion": rng.uniform(52, 72),
                "tradition": rng.uniform(42, 68),
            },
            "governance": {
                "form": "Hearth Council",
                "leader": None,
                "last_change_year": 1,
            },
            "settlements": [
                {"name": settlement, "founded_year": 1}
            ],
            "institutions": [],
            "discoveries": [],
            "notables": [],
            "pressures": {
                "scarcity": 0.0,
                "unrest": 0.0,
                "recovery": 0.0,
            },
            "population_milestones": [],
            "chronicle": [],
            "pending_notification_years": [],
        }
        self._add_event(
            state,
            "founding",
            f"{state['name']} was founded by {state['population']} settlers.",
            major=True,
            notify=False,
        )
        return state

    def _migrate_state(self, state: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        changed = False
        schema = int(state.get("schema_version", 1))

        if schema < 2:
            rng = random.Random(stable_seed(str(state.get("world_id", "tinyciv"))))
            state.setdefault("world_seed", rng.randrange(1, 2**63))
            state.setdefault("population_peak", int(state.get("population", 1)))
            state.setdefault("last_era", self._era(state))
            state.setdefault(
                "society",
                {
                    "traits": rng.sample(CULTURE_TRAITS, 2),
                    "cohesion": rng.uniform(52, 72),
                    "tradition": rng.uniform(42, 68),
                },
            )
            state.setdefault(
                "governance",
                {"form": "Hearth Council", "leader": None, "last_change_year": 1},
            )
            state.setdefault(
                "settlements",
                [{"name": self._root_settlement_name(str(state.get("name", "TinyCiv"))), "founded_year": 1}],
            )
            state.setdefault("institutions", [])
            state.setdefault("discoveries", [])
            state.setdefault("notables", [])
            state.setdefault("pressures", {"scarcity": 0.0, "unrest": 0.0, "recovery": 0.0})
            state.setdefault("population_milestones", [])
            state["schema_version"] = 2
            changed = True
            schema = 2

        # Defensive defaults for partially written or hand-edited saves.
        defaults: dict[str, Any] = {
            "status": "living",
            "chronicle": [],
            "last_visit_year": 0,
            "last_visit_at": None,
            "last_visit_snapshot": None,
            "population_peak": int(state.get("population", 1)),
            "population_milestones": [],
            "institutions": [],
            "discoveries": [],
            "notables": [],
            "pressures": {"scarcity": 0.0, "unrest": 0.0, "recovery": 0.0},
            "pending_notification_years": [],
        }
        for key, value in defaults.items():
            if key not in state:
                state[key] = value
                changed = True

        if schema != WORLD_SCHEMA:
            state["schema_version"] = WORLD_SCHEMA
            changed = True

        return state, changed

    def _load_or_create(self) -> dict[str, Any]:
        if STATE_PATH.exists():
            try:
                state = json.loads(STATE_PATH.read_text())
                state, changed = self._migrate_state(state)
                if changed:
                    self._save(state)
                return state
            except Exception as exc:
                print(f"TinyCiv: state file could not be read ({exc}); founding a new world.", flush=True)
        state = self._new_state()
        self._save(state)
        return state

    def _save(self, state: dict[str, Any] | None = None) -> None:
        state = state or self.state
        temp = STATE_PATH.with_suffix(".tmp")
        temp.write_text(json.dumps(state, indent=2))
        temp.replace(STATE_PATH)

    def _add_event(
        self,
        state: dict[str, Any],
        kind: str,
        text: str,
        *,
        major: bool = False,
        notify: bool = False,
    ) -> dict[str, Any]:
        event = {
            "id": str(uuid.uuid4()),
            "year": state["year"],
            "kind": kind,
            "text": text,
            "major": major,
            "notify": notify,
        }
        state["chronicle"].append(event)
        return event

    def _update_pressures(self, state: dict[str, Any]) -> None:
        p = state["pressures"]
        scarcity_target = max(0.0, 50.0 - state["food"]) * 1.4
        unrest_target = max(0.0, 52.0 - state["stability"]) + max(0.0, 45.0 - state["morale"]) * 0.7
        p["scarcity"] = clamp(p.get("scarcity", 0.0) * 0.72 + scarcity_target * 0.28)
        p["unrest"] = clamp(p.get("unrest", 0.0) * 0.76 + unrest_target * 0.24)
        if state["food"] > 58 and state["health"] > 58 and state["stability"] > 58:
            p["recovery"] = clamp(p.get("recovery", 0.0) + 4.0)
        else:
            p["recovery"] = clamp(p.get("recovery", 0.0) - 6.0)

    def _baseline_year(self, state: dict[str, Any]) -> None:
        society = state["society"]
        pressures = state["pressures"]

        state["knowledge"] = clamp(
            state["knowledge"]
            + random.uniform(0.12, 0.62)
            + max(0.0, society.get("cohesion", 50) - 50) * 0.002
        )
        state["food"] = clamp(
            state["food"]
            + random.uniform(-3.2, 3.2)
            - pressures.get("scarcity", 0.0) * 0.012
        )
        state["health"] = clamp(
            state["health"]
            + (state["food"] - 50) * 0.025
            + random.uniform(-1.7, 1.7)
        )
        state["morale"] = clamp(
            state["morale"]
            + (state["stability"] - 50) * 0.018
            + (state["food"] - 50) * 0.009
            + random.uniform(-1.9, 1.9)
        )
        state["stability"] = clamp(
            state["stability"]
            + (state["morale"] - 50) * 0.012
            + (society.get("cohesion", 50) - 50) * 0.012
            - pressures.get("unrest", 0.0) * 0.015
            + random.uniform(-1.35, 1.35)
        )

        society["cohesion"] = clamp(
            society.get("cohesion", 55)
            + (state["morale"] - 50) * 0.008
            + (state["stability"] - 50) * 0.006
            + random.uniform(-0.9, 0.9)
        )
        society["tradition"] = clamp(
            society.get("tradition", 55)
            + random.uniform(-0.65, 0.65)
            - max(0, state["knowledge"] - 55) * 0.003
        )

        quality = (state["food"] + state["health"] + state["morale"] + state["stability"]) / 400.0
        carrying_capacity = (
            80
            + (state["knowledge"] ** 2) * 8
            + len(state.get("settlements", [])) * 350
            + len(state.get("institutions", [])) * 260
        )
        density = state["population"] / max(1.0, carrying_capacity)
        density_pressure = max(0.0, density - 0.68) * 0.055
        if density > 0.72:
            state["food"] = clamp(state["food"] - (density - 0.72) * 1.8)
        growth_rate = -0.012 + quality * 0.043 - density_pressure + random.uniform(-0.011, 0.011)
        delta_float = state["population"] * growth_rate
        delta = math.floor(delta_float)
        fraction = delta_float - delta
        if random.random() < fraction:
            delta += 1
        if state["population"] < 40 and delta == 0 and quality > 0.58 and random.random() < 0.34:
            delta = 1
        state["population"] = max(2, state["population"] + delta)
        state["population_peak"] = max(int(state.get("population_peak", 0)), state["population"])

        self._update_pressures(state)

    def _event_harvest(self, state: dict[str, Any]) -> dict[str, Any]:
        poor_bias = clamp((55 - state["food"]) / 100, 0, 0.35)
        if random.random() < 0.45 + poor_bias:
            state["food"] = clamp(state["food"] - random.uniform(8, 19))
            state["morale"] = clamp(state["morale"] - random.uniform(2, 6))
            severe = state["food"] < 27
            return self._add_event(
                state,
                "harvest",
                "A poor harvest emptied storehouses faster than expected, and rationing followed.",
                major=severe,
                notify=severe,
            )
        state["food"] = clamp(state["food"] + random.uniform(9, 18))
        state["morale"] = clamp(state["morale"] + random.uniform(2, 6))
        return self._add_event(
            state,
            "harvest",
            "A remarkable harvest filled the storehouses and spilled into a season of feasts.",
        )

    def _event_illness(self, state: dict[str, Any]) -> dict[str, Any]:
        severity = random.uniform(0.018, 0.075) * (1.2 if state["health"] < 48 else 1.0)
        loss = max(1, int(round(state["population"] * severity)))
        state["population"] = max(2, state["population"] - loss)
        state["health"] = clamp(state["health"] - random.uniform(4, 10))
        severe = loss >= max(4, int(state["population"] * 0.07))
        return self._add_event(
            state,
            "illness",
            f"An illness moved through the settlements. {loss} lives were lost before it passed.",
            major=severe,
            notify=severe,
        )

    def _event_migration(self, state: dict[str, Any]) -> dict[str, Any]:
        if state["morale"] < 38 or state["stability"] < 34:
            loss = max(1, random.randint(1, max(2, int(math.sqrt(state["population"])))))
            state["population"] = max(2, state["population"] - loss)
            return self._add_event(
                state,
                "migration",
                f"Several households left in search of steadier ground. The population fell by {loss}.",
                major=loss >= 6,
                notify=False,
            )
        gain = random.randint(1, max(2, int(math.sqrt(state["population"]) + 1)))
        state["population"] += gain
        state["morale"] = clamp(state["morale"] + random.uniform(1, 4))
        state["population_peak"] = max(state["population_peak"], state["population"])
        return self._add_event(
            state,
            "migration",
            f"Travelers arrived and chose to remain. The population grew by {gain}.",
        )

    def _event_discovery(self, state: dict[str, Any]) -> dict[str, Any]:
        available = [d for d in DISCOVERIES if d[0] not in state["discoveries"] and state["knowledge"] >= d[1] - 7]
        if available:
            name, threshold = random.choice(available)
            state["discoveries"].append(name)
            state["knowledge"] = clamp(max(state["knowledge"], threshold) + random.uniform(1.5, 4.5))
            return self._add_event(
                state,
                "discovery",
                f"A breakthrough in {name} spread from workshop to workshop and changed ordinary life.",
                major=threshold >= 64,
                notify=threshold >= 82,
            )
        state["knowledge"] = clamp(state["knowledge"] + random.uniform(2.0, 5.0))
        return self._add_event(
            state,
            "discovery",
            "A stubborn practical problem was finally solved, and the method spread quickly.",
        )

    def _event_festival(self, state: dict[str, Any]) -> dict[str, Any]:
        state["morale"] = clamp(state["morale"] + random.uniform(3, 8))
        state["society"]["cohesion"] = clamp(state["society"].get("cohesion", 55) + random.uniform(2, 6))
        return self._add_event(
            state,
            "festival",
            "A communal festival outgrew its original purpose and became a tradition of its own.",
        )

    def _event_disaster(self, state: dict[str, Any]) -> dict[str, Any]:
        kind = random.choice(["fire", "storm", "flood"])
        state["stability"] = clamp(state["stability"] - random.uniform(4, 11))
        state["morale"] = clamp(state["morale"] - random.uniform(1, 5))
        if kind == "fire":
            text = "A night fire consumed homes and workshops before bucket lines contained it."
        elif kind == "storm":
            state["food"] = clamp(state["food"] - random.uniform(3, 10))
            text = "A violent storm tore through fields and roofs, leaving months of repairs behind."
        else:
            state["food"] = clamp(state["food"] - random.uniform(4, 12))
            text = "Floodwater crossed familiar boundaries and forced whole streets onto higher ground."
        severe = state["stability"] < 28 or state["food"] < 22
        return self._add_event(state, kind, text, major=severe, notify=severe)

    def _event_civic(self, state: dict[str, Any]) -> dict[str, Any]:
        if state["pressures"].get("unrest", 0) > 28 or state["stability"] < 45:
            state["stability"] = clamp(state["stability"] - random.uniform(2, 7))
            state["morale"] = clamp(state["morale"] - random.uniform(1, 5))
            return self._add_event(
                state,
                "dispute",
                "A bitter civic dispute split neighbors into camps before an uneasy compromise held.",
                major=state["stability"] < 25,
                notify=state["stability"] < 25,
            )
        state["stability"] = clamp(state["stability"] + random.uniform(2, 6))
        return self._add_event(
            state,
            "reform",
            "A set of ordinary rules was rewritten after years of complaint, and daily life became a little easier.",
        )

    def _event_notable(self, state: dict[str, Any]) -> dict[str, Any]:
        rng = random.Random(random.randrange(1, 2**63))
        person = self._person_name(rng)
        roles = ["builder", "healer", "teacher", "organizer", "keeper of records", "craftsperson", "explorer"]
        role = rng.choice(roles)
        state["notables"].append({"name": person, "role": role, "first_recorded_year": state["year"]})
        state["notables"] = state["notables"][-24:]
        effect = rng.choice(["knowledge", "health", "stability", "morale"])
        state[effect] = clamp(state[effect] + rng.uniform(1.5, 4.5))
        return self._add_event(
            state,
            "notable",
            f"{person}, a {role}, became widely known beyond their own neighborhood.",
        )

    def _event_institution(self, state: dict[str, Any]) -> dict[str, Any]:
        eligible = [
            item for item in INSTITUTIONS
            if item[0] not in state["institutions"]
            and state["population"] >= item[1]
            and state["knowledge"] >= item[2] - 8
        ]
        if not eligible:
            return self._event_civic(state)
        name, _, _ = random.choice(eligible)
        state["institutions"].append(name)
        state["stability"] = clamp(state["stability"] + random.uniform(2, 6))
        return self._add_event(
            state,
            "institution",
            f"The community established {name}, giving a permanent home to work once handled informally.",
            major=len(state["institutions"]) in {1, 4, 7},
            notify=False,
        )

    def _event_settlement(self, state: dict[str, Any]) -> dict[str, Any]:
        threshold = 65 * len(state["settlements"])
        used = {s["name"] for s in state["settlements"]}
        available = [n for n in SETTLEMENT_NAMES if n not in used]
        if state["population"] < threshold or not available:
            return self._event_migration(state)
        name = random.choice(available)
        state["settlements"].append({"name": name, "founded_year": state["year"]})
        state["morale"] = clamp(state["morale"] + random.uniform(1, 4))
        return self._add_event(
            state,
            "settlement",
            f"A permanent outlying settlement was founded at {name}.",
            major=True,
            notify=True,
        )

    def _event_conflict_or_recovery(self, state: dict[str, Any]) -> dict[str, Any]:
        if state["pressures"].get("unrest", 0) > 35:
            loss = max(0, int(state["population"] * random.uniform(0.0, 0.025)))
            state["population"] = max(2, state["population"] - loss)
            state["stability"] = clamp(state["stability"] - random.uniform(5, 12))
            state["morale"] = clamp(state["morale"] - random.uniform(3, 8))
            text = "A civic confrontation turned violent before exhausted mediators restored order."
            if loss:
                text += f" {loss} lives were lost."
            severe = state["stability"] < 24
            return self._add_event(state, "conflict", text, major=severe, notify=severe)
        state["food"] = clamp(state["food"] + random.uniform(3, 7))
        state["health"] = clamp(state["health"] + random.uniform(2, 5))
        state["stability"] = clamp(state["stability"] + random.uniform(2, 5))
        return self._add_event(
            state,
            "recovery",
            "Several uneventful seasons accumulated into something rare: broad, unmistakable prosperity.",
        )

    def _maybe_year_event(self, state: dict[str, Any]) -> dict[str, Any] | None:
        crisis = max(state["pressures"].get("scarcity", 0), state["pressures"].get("unrest", 0))
        event_chance = clamp(0.24 + crisis * 0.0022, 0.22, 0.48)
        if random.random() > event_chance:
            return None

        choices: list[tuple[float, Callable[[dict[str, Any]], dict[str, Any]]]] = [
            (15, self._event_harvest),
            (10, self._event_illness),
            (11, self._event_migration),
            (11, self._event_discovery),
            (10, self._event_festival),
            (10, self._event_disaster),
            (11, self._event_civic),
            (8, self._event_notable),
            (6, self._event_institution),
            (4, self._event_settlement),
            (4, self._event_conflict_or_recovery),
        ]
        funcs = [f for _, f in choices]
        weights = [w for w, _ in choices]
        return random.choices(funcs, weights=weights, k=1)[0](state)

    def _maybe_governance_event(self, state: dict[str, Any]) -> dict[str, Any] | None:
        gov = state["governance"]
        leader = gov.get("leader")
        if leader:
            if state["year"] >= int(leader.get("until_year", state["year"] + 1)):
                old_name = leader["name"]
                new_name = self._person_name()
                tenure = random.randint(6, 13)
                gov["leader"] = {
                    "name": new_name,
                    "title": leader.get("title", "First Speaker"),
                    "since_year": state["year"],
                    "until_year": state["year"] + tenure,
                }
                gov["last_change_year"] = state["year"]
                return self._add_event(
                    state,
                    "succession",
                    f"{old_name} left civic office. {new_name} was chosen to succeed them.",
                    major=False,
                    notify=False,
                )
            return None

        if state["year"] >= 5 and (state["population"] >= 22 or random.random() < 0.08):
            name = self._person_name()
            tenure = random.randint(7, 14)
            gov["leader"] = {
                "name": name,
                "title": "First Speaker",
                "since_year": state["year"],
                "until_year": state["year"] + tenure,
            }
            gov["last_change_year"] = state["year"]
            return self._add_event(
                state,
                "governance",
                f"For the first time, the council entrusted one speaker with a defined civic term: {name}.",
                major=True,
                notify=False,
            )
        return None

    def _maybe_population_milestone(self, state: dict[str, Any]) -> dict[str, Any] | None:
        seen = set(state.get("population_milestones", []))
        reached = [m for m in POPULATION_MILESTONES if state["population"] >= m and m not in seen]
        if not reached:
            return None
        milestone = max(reached)
        state["population_milestones"].extend(m for m in reached if m not in seen)
        return self._add_event(
            state,
            "population_milestone",
            f"The population passed {milestone:,} for the first time.",
            major=True,
            notify=milestone >= 100,
        )

    def _maybe_era_change(self, state: dict[str, Any]) -> dict[str, Any] | None:
        current = self._era(state)
        previous = state.get("last_era", current)
        if current == previous:
            return None
        state["last_era"] = current
        return self._add_event(
            state,
            "era",
            f"Later chroniclers marked Year {state['year']} as the beginning of the {current}.",
            major=True,
            notify=True,
        )

    def _last_hearth_guard(self, state: dict[str, Any]) -> dict[str, Any] | None:
        if state["population"] <= 2 and (
            state["food"] < 18 or state["health"] < 18 or state["stability"] < 18
        ):
            state["food"] = max(state["food"], 34)
            state["health"] = max(state["health"], 34)
            state["stability"] = max(state["stability"], 34)
            state["morale"] = max(state["morale"], 31)
            return self._add_event(
                state,
                "last_hearth",
                "Only a final hearth remained. Against absurd odds, it endured and began rebuilding.",
                major=True,
                notify=True,
            )
        return None

    def _year_tick(self, state: dict[str, Any]) -> list[dict[str, Any]]:
        generated: list[dict[str, Any]] = []
        state["year"] += 1
        self._baseline_year(state)

        event = self._maybe_year_event(state)
        if event:
            generated.append(event)

        governance_event = self._maybe_governance_event(state)
        if governance_event:
            generated.append(governance_event)

        milestone = self._maybe_population_milestone(state)
        if milestone:
            generated.append(milestone)

        era_event = self._maybe_era_change(state)
        if era_event:
            generated.append(era_event)

        if state["year"] % 25 == 0:
            generated.append(
                self._add_event(
                    state,
                    "milestone",
                    f"{state['name']} reached Year {state['year']} with a population of {state['population']}.",
                    major=True,
                    notify=True,
                )
            )

        guard = self._last_hearth_guard(state)
        if guard:
            generated.append(guard)

        return generated

    def advance_to_now(self) -> list[dict[str, Any]]:
        with self._lock:
            now = utc_now()
            last = parse_iso(self.state["last_simulated_at"])
            elapsed_seconds = max(0, (now - last).total_seconds())
            years_due = int(elapsed_seconds // YEAR_SECONDS)
            if years_due <= 0:
                return []

            years_due = min(years_due, 10_000)
            generated: list[dict[str, Any]] = []
            pending = self.state.setdefault("pending_notification_years", [])
            for _ in range(years_due):
                year_events = self._year_tick(self.state)
                generated.extend(year_events)
                if year_events:
                    year = int(self.state["year"])
                    if year not in pending:
                        pending.append(year)

            simulated_until = last.timestamp() + years_due * YEAR_SECONDS
            self.state["last_simulated_at"] = iso(datetime.fromtimestamp(simulated_until, tz=timezone.utc))
            self._save()
            return generated


    def pending_notification_years(self) -> list[int]:
        with self._lock:
            return [int(year) for year in self.state.get("pending_notification_years", [])]

    def acknowledge_notification_year(self, year: int) -> None:
        with self._lock:
            pending = self.state.setdefault("pending_notification_years", [])
            updated = [int(item) for item in pending if int(item) != int(year)]
            if updated != pending:
                self.state["pending_notification_years"] = updated
                self._save()

    def _metric_snapshot(self, state: dict[str, Any] | None = None) -> dict[str, int]:
        s = state or self.state
        return {
            "population": int(s["population"]),
            "food": round(s["food"]),
            "health": round(s["health"]),
            "morale": round(s["morale"]),
            "knowledge": round(s["knowledge"]),
            "stability": round(s["stability"]),
        }

    def public_state(
        self,
        chronicle_page: int = 1,
        chronicle_order: str = "desc",
        page_size: int = 12,
    ) -> dict[str, Any]:
        with self._lock:
            self.advance_to_now()
            s = self.state

            order = "asc" if chronicle_order == "asc" else "desc"
            page_size = max(1, min(int(page_size), 50))
            total_entries = len(s["chronicle"])
            total_pages = max(1, math.ceil(total_entries / page_size))
            page = max(1, min(int(chronicle_page), total_pages))

            entries = s["chronicle"] if order == "asc" else list(reversed(s["chronicle"]))
            start = (page - 1) * page_size
            chronicle_page_entries = entries[start:start + page_size]

            return {
                "world_id": s["world_id"],
                "name": s["name"],
                "status": s["status"],
                "founded_at": s["founded_at"],
                "year": s["year"],
                "era": self._era(s),
                "population": s["population"],
                "metrics": {
                    "food": round(s["food"]),
                    "health": round(s["health"]),
                    "morale": round(s["morale"]),
                    "knowledge": round(s["knowledge"]),
                    "stability": round(s["stability"]),
                },
                "chronicle": chronicle_page_entries,
                "chronicle_pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_entries": total_entries,
                    "total_pages": total_pages,
                    "order": order,
                },
            }

    def visit(self) -> dict[str, Any]:
        with self._lock:
            self.advance_to_now()
            current_year = self.state["year"]
            last_year = self.state.get("last_visit_year", 0)
            unseen = [e for e in self.state["chronicle"] if e["year"] > last_year]
            previous_snapshot = self.state.get("last_visit_snapshot")
            current_snapshot = self._metric_snapshot()

            if last_year == 0:
                report = {
                    "years_away": 0,
                    "headline": f"You arrive in Year {current_year}.",
                    "events": unseen[-8:],
                    "omitted_count": max(0, len(unseen) - 8),
                    "metric_baseline": previous_snapshot,
                }
            else:
                years_away = max(0, current_year - last_year)
                if years_away == 0:
                    headline = "No civilization years have passed since your last visit."
                elif years_away == 1:
                    headline = "One civilization year has passed since your last visit."
                else:
                    headline = f"{years_away} civilization years have passed since your last visit."
                report = {
                    "years_away": years_away,
                    "headline": headline,
                    "events": unseen[-8:],
                    "omitted_count": max(0, len(unseen) - 8),
                    "metric_baseline": previous_snapshot,
                }

            self.state["last_visit_year"] = current_year
            self.state["last_visit_at"] = iso(utc_now())
            self.state["last_visit_snapshot"] = current_snapshot
            self._save()
            return {"report": report, "state": self.public_state()}

    def nuke(self) -> dict[str, Any]:
        with self._lock:
            self.state = self._new_state()
            self._save()
            return self.public_state()
