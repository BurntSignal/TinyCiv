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
WORLD_SCHEMA = 6

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

PUBLIC_WORKS = [
    ("lined communal wells", 18, 10),
    ("raised field drains", 24, 13),
    ("a timber bridge over the nearest difficult crossing", 30, 16),
    ("stone-lined irrigation channels", 42, 20),
    ("a maintained road between the largest settlements", 70, 25),
    ("a permanent public square", 95, 28),
    ("a covered market hall", 150, 34),
    ("a network of public cisterns", 240, 40),
]

GEOGRAPHIC_DISCOVERIES = [
    ("north_pass", 14, 8, "Explorers returned with a reliable route through high ground once treated as an impassable boundary."),
    ("great_river", 20, 10, "An expedition followed an unfamiliar watercourse for days and returned convinced it was part of a river far larger than any previously mapped."),
    ("salt_marsh", 24, 12, "Travelers found broad salt marshes beyond the familiar country and returned with enough salt to make the discovery impossible to ignore."),
    ("ore_hills", 30, 16, "Prospectors identified dark, metal-bearing stone in distant hills and marked the route for later journeys."),
    ("far_lake", 38, 18, "Explorers reached a vast inland lake beyond the known trails and brought home the first dependable account of its shores."),
    ("old_foundations", 45, 22, "A scouting party found weathered stone foundations far from any living settlement known to them. No one could say who had built them."),
    ("coast", 60, 27, "After a long expedition, travelers returned with shells, salt-stiff clothing, and descriptions of water stretching beyond the horizon."),
]

ECONOMIC_DEVELOPMENTS = [
    ("market_day", 18, 8, "A regular market day took hold, drawing farmers and craftworkers into the same place often enough to reshape local exchange."),
    ("specialist_crafts", 24, 12, "Some households began living primarily by a single craft rather than dividing their time between every necessary task."),
    ("apprenticeships", 35, 16, "Formal apprenticeships became common enough that skilled trades started passing from masters to students in recognizable lineages."),
    ("long_distance_carriers", 55, 20, "A small class of carriers began making regular journeys between settlements, moving goods for people they scarcely knew."),
    ("seasonal_fair", 80, 24, "A seasonal fair grew into the largest recurring exchange of goods, labor, news, and gossip in the region."),
    ("workshop_district", 125, 31, "Workshops clustered into a noisy district where tools, labor, and specialized knowledge moved quickly from one craft to another."),
]

CULTURAL_DEVELOPMENTS = [
    ("lantern_night", 12, 0, "An evening of shared lamps and stories outlasted the occasion that created it and became an annual tradition."),
    ("ancestor_hearths", 16, 0, "Families began keeping small memorial hearths for the dead, turning private mourning into a recognizable custom."),
    ("public_storykeepers", 22, 10, "A handful of gifted storytellers became trusted keepers of old accounts, preserving events that had previously survived only by chance."),
    ("founding_day", 28, 0, "The founding of the settlement became the center of a yearly public observance, complete with traditions no founder would have recognized."),
    ("watcher_belief", 32, 12, "A belief spread that an unseen watcher beyond the world sometimes turned its attention toward {root}. Small offerings began appearing on rooftops and thresholds."),
    ("funerary_cairns", 38, 12, "Stone cairns marking the dead became common enough to change the landscape around the oldest roads."),
    ("public_music", 45, 15, "Distinctive local songs and instruments became associated with public gatherings, work crews, and celebrations."),
    ("philosophers", 70, 26, "Public arguments about duty, nature, and the good life became a recognized pursuit rather than merely an excuse to linger after meals."),
]

POPULATION_MILESTONES = [25, 50, 100, 250, 500, 1000, 2500, 5000, 10000, 25000, 50000, 100000]

WIDER_WORLD_NAMES = [
    "Alderreach", "Bellmere", "Cairnwatch", "Duskford", "Eastmere",
    "Fallowmark", "Greyhaven", "Highfen", "Kestrel Vale", "Larkspur",
    "Northbarrow", "Orchard Reach", "Redwillow", "Stonecross", "Sunmere",
    "Thornwall", "Valewick", "Whiteharbor", "Windmere", "Yarrowfield",
]



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
            "civilization_memory": {
                "traditions": [],
                "public_works": [],
                "geography": [],
                "economic_changes": [],
            },
            "pressures": {
                "scarcity": 0.0,
                "unrest": 0.0,
                "recovery": 0.0,
            },
            "population_milestones": [],
            "chronicle": [],
            "wider_world": {
                "contacts": [],
                "next_check_year": rng.randint(28, 40),
                "last_event_year": 0,
            },
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
            "civilization_memory": {
                "traditions": [],
                "public_works": [],
                "geography": [],
                "economic_changes": [],
            },
            "pressures": {"scarcity": 0.0, "unrest": 0.0, "recovery": 0.0},
            "pending_notification_years": [],
        }
        for key, value in defaults.items():
            if key not in state:
                state[key] = value
                changed = True

        memory = state.get("civilization_memory")
        if not isinstance(memory, dict):
            memory = {}
            state["civilization_memory"] = memory
            changed = True
        for key in ("traditions", "public_works", "geography", "economic_changes"):
            if key not in memory or not isinstance(memory.get(key), list):
                memory[key] = []
                changed = True

        if "wider_world" not in state or not isinstance(state.get("wider_world"), dict):
            rng = random.Random(stable_seed(f"{state.get('world_id', 'tinyciv')}:wider-world"))
            current_year = int(state.get("year", 1))
            state["wider_world"] = {
                "contacts": [],
                "next_check_year": max(28, current_year + rng.randint(5, 14)),
                "last_event_year": 0,
            }
            changed = True
        else:
            wider = state["wider_world"]
            if "contacts" not in wider or not isinstance(wider.get("contacts"), list):
                wider["contacts"] = []
                changed = True
            if "next_check_year" not in wider:
                wider["next_check_year"] = max(28, int(state.get("year", 1)) + 8)
                changed = True
            if "last_event_year" not in wider:
                wider["last_event_year"] = 0
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
            if severe:
                loss = max(1, int(round(state["population"] * random.uniform(0.01, 0.045))))
                state["population"] = max(2, state["population"] - loss)
                state["health"] = clamp(state["health"] - random.uniform(3, 8))
                lives = "life was" if loss == 1 else "lives were"
                return self._add_event(
                    state,
                    "famine",
                    f"A failed harvest became a famine. Stores ran dangerously low, rationing spread, and {loss} {lives} lost before food supplies recovered.",
                    major=True,
                    notify=True,
                )
            return self._add_event(
                state,
                "harvest",
                "A poor harvest emptied storehouses faster than expected, and rationing followed.",
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
        lives = "life was" if loss == 1 else "lives were"
        return self._add_event(
            state,
            "illness",
            f"An illness moved through the settlements. {loss} {lives} lost before it passed.",
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
            random.choice([
                "A stubborn practical problem was finally solved, and the method spread quickly between households and workshops.",
                "A practical technique that had existed in fragments was finally understood well enough to teach reliably.",
                "Several small improvements came together into a method useful enough that people began copying it almost immediately.",
            ]),
        )

    def _event_public_works(self, state: dict[str, Any]) -> dict[str, Any]:
        memory = state["civilization_memory"]["public_works"]
        eligible = [
            item for item in PUBLIC_WORKS
            if item[0] not in memory
            and state["population"] >= item[1]
            and state["knowledge"] >= item[2] - 5
        ]
        if not eligible:
            return self._event_economy(state)

        name, _, _ = random.choice(eligible)
        memory.append(name)
        state["stability"] = clamp(state["stability"] + random.uniform(1.0, 4.0))
        state["food"] = clamp(state["food"] + random.uniform(0.0, 3.0))
        return self._add_event(
            state,
            "public_works",
            f"A coordinated public effort completed {name}, permanently changing how people moved, worked, or gathered.",
            major=len(memory) in {1, 4, 7},
        )

    def _event_exploration(self, state: dict[str, Any]) -> dict[str, Any]:
        memory = state["civilization_memory"]["geography"]
        eligible = [
            item for item in GEOGRAPHIC_DISCOVERIES
            if item[0] not in memory
            and state["population"] >= item[1]
            and state["knowledge"] >= item[2] - 5
        ]
        if not eligible:
            state["knowledge"] = clamp(state["knowledge"] + random.uniform(0.8, 2.2))
            return self._add_event(
                state,
                "exploration",
                "A long-ranging party returned with corrected routes and descriptions of country that had existed only as rumor on earlier maps.",
            )

        key, _, _, text = random.choice(eligible)
        memory.append(key)
        state["knowledge"] = clamp(state["knowledge"] + random.uniform(1.0, 3.0))
        state["morale"] = clamp(state["morale"] + random.uniform(0.0, 2.0))
        return self._add_event(state, "exploration", text, major=key in {"old_foundations", "coast"})

    def _event_economy(self, state: dict[str, Any]) -> dict[str, Any]:
        memory = state["civilization_memory"]["economic_changes"]
        eligible = [
            item for item in ECONOMIC_DEVELOPMENTS
            if item[0] not in memory
            and state["population"] >= item[1]
            and state["knowledge"] >= item[2] - 5
        ]
        if eligible:
            key, _, _, text = random.choice(eligible)
            memory.append(key)
            text = text.format(root=self._root_settlement_name(state["name"]))
        else:
            text = random.choice([
                "A run of unusually strong demand changed which goods were worth carrying between settlements, and several households changed trades in response.",
                "A shortage in one settlement and a surplus in another turned an occasional exchange route into a dependable habit.",
                "Local producers began pooling transport and storage, allowing goods to travel farther before being consumed or traded.",
            ])
        state["food"] = clamp(state["food"] + random.uniform(0.5, 3.0))
        state["stability"] = clamp(state["stability"] + random.uniform(0.0, 2.0))
        return self._add_event(state, "economy", text)

    def _event_culture(self, state: dict[str, Any]) -> dict[str, Any]:
        memory = state["civilization_memory"]["traditions"]
        eligible = [
            item for item in CULTURAL_DEVELOPMENTS
            if item[0] not in memory
            and state["year"] >= item[1]
            and state["knowledge"] >= item[2] - 5
        ]
        if eligible:
            key, _, _, text = random.choice(eligible)
            memory.append(key)
        else:
            text = random.choice([
                "A local custom spread beyond the neighborhood that created it and became something people increasingly described as simply 'the way we do things.'",
                "A once-private celebration became a public tradition after neighboring settlements began copying it in their own fashion.",
                "Old stories were gathered, argued over, and retold until a shared version began to take shape across the settlements.",
            ])
        state["morale"] = clamp(state["morale"] + random.uniform(1.0, 4.0))
        state["society"]["cohesion"] = clamp(state["society"].get("cohesion", 55) + random.uniform(1.0, 3.5))
        state["society"]["tradition"] = clamp(state["society"].get("tradition", 55) + random.uniform(0.5, 2.5))
        return self._add_event(state, "culture", text, major=bool(eligible and key == "watcher_belief"))

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
        deeds = {
            "builder": [
                "organized repairs after repeated structural failures and left behind building practices copied for years",
                "designed a difficult public structure that other builders soon began imitating",
            ],
            "healer": [
                "assembled a practical collection of remedies and observations that other healers began consulting",
                "organized care during a season of widespread sickness and changed how the community responded to outbreaks",
            ],
            "teacher": [
                "trained enough students that their method of instruction spread well beyond a single household",
                "opened lessons to children outside their own kin group, an idea that proved unexpectedly durable",
            ],
            "organizer": [
                "coordinated a difficult communal project that had defeated several earlier attempts",
                "built a network of mutual aid between neighborhoods that survived long after the original crisis passed",
            ],
            "keeper of records": [
                "compiled scattered accounts into a record later chroniclers would repeatedly rely upon",
                "introduced a more dependable way to preserve agreements, births, deaths, and public decisions",
            ],
            "craftsperson": [
                "perfected a difficult technique and taught it freely enough to transform several local workshops",
                "produced work of such unusual quality that apprentices traveled from other settlements to study it",
            ],
            "explorer": [
                "returned from a dangerous expedition with route notes that opened previously avoided country to regular travel",
                "led several expeditions into poorly known country and produced the first maps people trusted with their lives",
            ],
        }
        deed = rng.choice(deeds[role])
        return self._add_event(state, "notable", f"{person}, a {role}, {deed}.")

    def _event_institution(self, state: dict[str, Any]) -> dict[str, Any]:
        eligible = [
            item for item in INSTITUTIONS
            if item[0] not in state["institutions"]
            and state["population"] >= item[1]
            and state["knowledge"] >= item[2] - 8
        ]
        if not eligible:
            return self._event_public_works(state)
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

    def _new_wider_world_contact(self, state: dict[str, Any]) -> dict[str, Any]:
        wider = state["wider_world"]
        used = {str(contact.get("name", "")) for contact in wider.get("contacts", [])}
        available = [name for name in WIDER_WORLD_NAMES if name not in used]
        name = random.choice(available) if available else f"Far Settlement {len(used) + 1}"
        return {
            "id": str(uuid.uuid4()),
            "name": name,
            "stage": 1,
            "first_hint_year": state["year"],
            "last_contact_year": state["year"],
            "relation": random.uniform(44, 62),
            "trade_established": False,
        }

    def _wider_world_first_hint(self, state: dict[str, Any]) -> dict[str, Any]:
        wider = state["wider_world"]
        contact = self._new_wider_world_contact(state)
        wider["contacts"].append(contact)
        root = self._root_settlement_name(state["name"])
        texts = [
            f"Explorers returned to {root} with reports of distant smoke columns and cultivated fields beyond lands previously known to them.",
            f"Travelers brought persistent stories to {root} of a settled people living far beyond the familiar frontier.",
            f"A scouting party returned to {root} carrying worked goods unlike anything made locally, obtained from strangers beyond the known lands.",
        ]
        return self._add_event(state, "distant_people", random.choice(texts), major=True, notify=True)

    def _wider_world_direct_contact(self, state: dict[str, Any], contact: dict[str, Any]) -> dict[str, Any]:
        contact["stage"] = 2
        contact["last_contact_year"] = state["year"]
        root = self._root_settlement_name(state["name"])
        name = contact["name"]
        texts = [
            f"An expedition returned to {root} after meeting people from a distant land. They called their homeland {name}.",
            f"For the first time, travelers from {name} reached {root}, confirming years of stories about another settled people.",
            f"Explorers from {root} made peaceful contact with people of {name} and returned with the first reliable account of their homeland.",
        ]
        state["knowledge"] = clamp(state["knowledge"] + random.uniform(0.5, 2.0))
        state["morale"] = clamp(state["morale"] + random.uniform(-0.5, 2.5))
        return self._add_event(state, "first_contact", random.choice(texts), major=True, notify=True)

    def _wider_world_exchange(self, state: dict[str, Any], contact: dict[str, Any]) -> dict[str, Any]:
        contact["stage"] = 3
        contact["last_contact_year"] = state["year"]
        contact["trade_established"] = True
        name = contact["name"]
        root = self._root_settlement_name(state["name"])
        texts = [
            f"A small delegation from {name} arrived in {root} to discuss regular exchange of goods between the two peoples.",
            f"Merchants from {name} reached {root} with goods for barter, beginning the first sustained exchange beyond {root}'s own settlements.",
            f"Representatives of {name} spent a season in {root}. By the time they departed, both sides had agreed to keep a regular route open.",
        ]
        state["food"] = clamp(state["food"] + random.uniform(1.0, 4.0))
        state["knowledge"] = clamp(state["knowledge"] + random.uniform(1.0, 3.0))
        state["morale"] = clamp(state["morale"] + random.uniform(0.5, 2.5))
        return self._add_event(state, "foreign_exchange", random.choice(texts), major=True, notify=True)

    def _wider_world_ongoing(self, state: dict[str, Any], contact: dict[str, Any]) -> dict[str, Any]:
        name = contact["name"]
        contact["last_contact_year"] = state["year"]
        relation = clamp(float(contact.get("relation", 52)) + random.uniform(-8, 8))
        contact["relation"] = relation

        roll = random.random()
        if relation < 32 and roll < 0.58:
            state["stability"] = clamp(state["stability"] - random.uniform(1.5, 4.5))
            state["morale"] = clamp(state["morale"] - random.uniform(0.5, 3.0))
            contact["relation"] = clamp(relation - random.uniform(1, 5))
            texts = [
                f"A dispute with travelers from {name} disrupted the familiar route between the two peoples for a time.",
                f"Trade with {name} slowed after a series of accusations neither side could easily settle.",
                f"Messengers returned from {name} without agreement on a growing border dispute, leaving relations noticeably colder.",
            ]
            return self._add_event(state, "foreign_tension", random.choice(texts), major=relation < 20, notify=relation < 20)

        if roll < 0.28:
            gain = max(1, random.randint(1, max(2, int(math.sqrt(state["population"]) * 0.35))))
            state["population"] += gain
            state["population_peak"] = max(state["population_peak"], state["population"])
            state["morale"] = clamp(state["morale"] + random.uniform(0.5, 2.5))
            return self._add_event(
                state,
                "foreign_migration",
                f"Several families from {name} chose to settle permanently among the people of {self._root_settlement_name(state['name'])}.",
            )

        if roll < 0.62:
            state["food"] = clamp(state["food"] + random.uniform(1.0, 4.5))
            state["morale"] = clamp(state["morale"] + random.uniform(0.5, 2.0))
            contact["relation"] = clamp(relation + random.uniform(1, 4))
            texts = [
                f"A busy season of trade with {name} brought unfamiliar goods into local markets and carried local wares outward in return.",
                f"Caravans traveling between {name} and {self._root_settlement_name(state['name'])} became common enough to stop drawing crowds.",
                f"A difficult harvest was softened by goods arriving along the established route from {name}.",
            ]
            return self._add_event(state, "foreign_trade", random.choice(texts))

        state["knowledge"] = clamp(state["knowledge"] + random.uniform(1.0, 3.5))
        contact["relation"] = clamp(relation + random.uniform(0, 3))
        texts = [
            f"Craftworkers returning from {name} introduced methods that quickly found uses in local workshops.",
            f"Visitors from {name} exchanged practical knowledge with local builders, healers, and record keepers.",
            f"A delegation traveled to {name} and returned with observations that challenged several long-held assumptions.",
        ]
        return self._add_event(state, "foreign_knowledge", random.choice(texts))

    def _maybe_wider_world_event(self, state: dict[str, Any]) -> dict[str, Any] | None:
        wider = state.get("wider_world")
        if not isinstance(wider, dict):
            return None
        year = int(state["year"])
        next_check = int(wider.get("next_check_year", 28))
        if year < next_check:
            return None

        # Wider-world developments are intentionally sparse. The simulation keeps
        # the machinery private; only Chronicle-worthy consequences are public.
        wider["next_check_year"] = year + random.randint(4, 12)
        contacts = wider.setdefault("contacts", [])
        explorer_known = any(str(n.get("role", "")) == "explorer" for n in state.get("notables", []))
        outward_capacity = state["knowledge"] + math.sqrt(max(1, state["population"])) * 1.8 + len(state.get("settlements", [])) * 2.5

        if not contacts:
            if year < 28 or (outward_capacity < 20 and not explorer_known):
                return None
            chance = clamp(0.28 + max(0.0, outward_capacity - 20) * 0.012, 0.28, 0.72)
            if random.random() > chance:
                return None
            event = self._wider_world_first_hint(state)
            wider["last_event_year"] = year
            return event

        # Once first contact is established, later civilizations can independently
        # enter the Chronicle as TinyCiv's reach and knowledge expand.
        mature_contacts = [c for c in contacts if int(c.get("stage", 1)) >= 3]
        oldest_hint = min(int(c.get("first_hint_year", year)) for c in contacts)
        can_find_another = (
            len(contacts) < 3
            and mature_contacts
            and year - oldest_hint >= 24
            and (state["knowledge"] >= 28 or state["population"] >= 70)
        )
        if can_find_another and random.random() < 0.18:
            event = self._wider_world_first_hint(state)
            wider["last_event_year"] = year
            return event

        contact = random.choice(contacts)
        stage = int(contact.get("stage", 1))
        years_since = year - int(contact.get("last_contact_year", contact.get("first_hint_year", year)))
        if stage == 1:
            if years_since < 3 or random.random() > 0.72:
                return None
            event = self._wider_world_direct_contact(state, contact)
        elif stage == 2:
            if years_since < 2 or random.random() > 0.78:
                return None
            event = self._wider_world_exchange(state, contact)
        else:
            if years_since < 4 or random.random() > 0.68:
                return None
            event = self._wider_world_ongoing(state, contact)

        wider["last_event_year"] = year
        return event

    def _maybe_year_event(self, state: dict[str, Any]) -> dict[str, Any] | None:
        crisis = max(state["pressures"].get("scarcity", 0), state["pressures"].get("unrest", 0))
        event_chance = clamp(0.28 + crisis * 0.0022, 0.26, 0.50)
        if random.random() > event_chance:
            return None

        choices: list[tuple[float, Callable[[dict[str, Any]], dict[str, Any]]]] = [
            (13, self._event_harvest),
            (8, self._event_illness),
            (8, self._event_migration),
            (12, self._event_discovery),
            (7, self._event_festival),
            (9, self._event_disaster),
            (4, self._event_civic),
            (6, self._event_notable),
            (7, self._event_institution),
            (9, self._event_public_works),
            (9, self._event_exploration),
            (9, self._event_economy),
            (10, self._event_culture),
            (4, self._event_settlement),
            (5, self._event_conflict_or_recovery),
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

                # Routine succession is background administration, not history.
                # Only a transition that becomes consequential earns Chronicle ink.
                unrest = float(state["pressures"].get("unrest", 0))
                instability = max(0.0, 52.0 - float(state["stability"]))
                consequential_chance = clamp(0.03 + unrest * 0.008 + instability * 0.009, 0.03, 0.58)
                if random.random() > consequential_chance:
                    return None

                severe = state["stability"] < 34 or unrest > 36
                if severe and random.random() < 0.18:
                    state["stability"] = clamp(state["stability"] - random.uniform(4, 9))
                    state["morale"] = clamp(state["morale"] - random.uniform(2, 6))
                    text = (
                        f"{old_name} was killed during a violent struggle over civic succession. "
                        f"After days of uncertainty, {new_name} emerged as the new First Speaker."
                    )
                    return self._add_event(state, "violent_succession", text, major=True, notify=True)

                state["stability"] = clamp(state["stability"] - random.uniform(1, 5))
                texts = [
                    f"The transfer of civic office from {old_name} to {new_name} was bitterly disputed, splitting the council and drawing crowds into the streets before the result held.",
                    f"{old_name} resisted leaving civic office at the end of the term. Weeks of public pressure and council maneuvering ended with {new_name} taking the seat.",
                    f"The succession of {new_name} after {old_name} triggered the first serious challenge to how civic authority was transferred, forcing the council to rewrite its own rules.",
                ]
                return self._add_event(state, "contested_succession", random.choice(texts), major=severe, notify=severe)
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

        wider_world_event = self._maybe_wider_world_event(state)
        if wider_world_event:
            generated.append(wider_world_event)

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

    def chronicle_export(self) -> dict[str, Any]:
        with self._lock:
            self.advance_to_now()
            s = self.state
            return {
                "name": s["name"],
                "year": s["year"],
                "era": self._era(s),
                "chronicle": list(s["chronicle"]),
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
