\
from __future__ import annotations

import json
import math
import os
import random
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

YEAR_SECONDS = int(os.getenv("TINYCIV_YEAR_SECONDS", "3600"))
DATA_DIR = Path(os.getenv("TINYCIV_DATA_DIR", "/data"))
STATE_PATH = DATA_DIR / "tinyciv_state.json"
MAX_CHRONICLE = 300

SETTLEMENT_NAMES = [
    "Mossvale", "Brasswick", "Fernhollow", "Emberford", "Tinkerfen",
    "Rookhaven", "Thistlebarrow", "Coppermere", "Lanternreach", "Oakrest",
]

FOUNDING_TITLES = [
    "Compact", "Commonwealth", "Hearth", "Settlement", "Freehold", "Union",
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


def clamp(value: float, low: float = 0, high: float = 100) -> float:
    return max(low, min(high, value))


class TinyCivEngine:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.state = self._load_or_create()

    def _new_state(self) -> dict[str, Any]:
        now = utc_now()
        settlement = random.choice(SETTLEMENT_NAMES)
        title = random.choice(FOUNDING_TITLES)
        state = {
            "world_id": str(uuid.uuid4()),
            "name": f"{settlement} {title}",
            "status": "living",
            "founded_at": iso(now),
            "last_simulated_at": iso(now),
            "last_visit_at": None,
            "last_visit_year": 0,
            "year": 1,
            "population": random.randint(11, 17),
            "food": random.randint(62, 78),
            "health": random.randint(68, 82),
            "morale": random.randint(60, 78),
            "knowledge": random.randint(5, 12),
            "stability": random.randint(65, 82),
            "chronicle": [],
        }
        self._add_event(
            state,
            "founding",
            f"{state['name']} was founded by {state['population']} settlers.",
            major=True,
            notify=False,
        )
        return state

    def _load_or_create(self) -> dict[str, Any]:
        if STATE_PATH.exists():
            try:
                return json.loads(STATE_PATH.read_text())
            except Exception as exc:
                print(f"TinyCiv: state file could not be read ({exc}); founding a new world.")
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
        state["chronicle"] = state["chronicle"][-MAX_CHRONICLE:]
        return event

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

    def _year_tick(self, state: dict[str, Any]) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        state["year"] += 1

        # Slow-moving baseline conditions.
        state["knowledge"] = clamp(state["knowledge"] + random.uniform(0.15, 0.75))
        state["food"] = clamp(state["food"] + random.uniform(-3.0, 3.0))
        state["health"] = clamp(
            state["health"] + (state["food"] - 50) * 0.025 + random.uniform(-1.8, 1.8)
        )
        state["morale"] = clamp(
            state["morale"]
            + (state["stability"] - 50) * 0.018
            + random.uniform(-2.0, 2.0)
        )
        state["stability"] = clamp(
            state["stability"]
            + (state["morale"] - 50) * 0.012
            + random.uniform(-1.5, 1.5)
        )

        # Population growth is intentionally gentle. Good years compound; bad years stall.
        quality = (
            state["food"] + state["health"] + state["morale"] + state["stability"]
        ) / 400.0
        growth_rate = -0.012 + (quality * 0.043) + random.uniform(-0.012, 0.012)
        delta = int(round(state["population"] * growth_rate))

        # Tiny populations should still be capable of growing.
        if state["population"] < 40 and delta == 0 and random.random() < 0.45:
            delta = 1
        state["population"] = max(2, state["population"] + delta)

        # Ordinary chronicle events.
        roll = random.random()

        if roll < 0.035:
            loss = max(1, int(state["population"] * random.uniform(0.03, 0.09)))
            state["population"] = max(2, state["population"] - loss)
            state["health"] = clamp(state["health"] - random.uniform(5, 11))
            event = self._add_event(
                state,
                "illness",
                f"An illness swept through the settlement. {loss} lives were lost before it passed.",
                major=loss >= 4,
                notify=loss >= 4,
            )
            events.append(event)

        elif roll < 0.070:
            state["food"] = clamp(state["food"] - random.uniform(10, 22))
            state["morale"] = clamp(state["morale"] - random.uniform(3, 8))
            event = self._add_event(
                state,
                "harvest",
                "A poor harvest emptied storehouses and made the coming season uneasy.",
                major=state["food"] < 30,
                notify=state["food"] < 30,
            )
            events.append(event)

        elif roll < 0.105:
            state["food"] = clamp(state["food"] + random.uniform(10, 20))
            state["morale"] = clamp(state["morale"] + random.uniform(3, 7))
            event = self._add_event(
                state,
                "harvest",
                "A remarkable harvest filled the storehouses and sparked a long communal feast.",
            )
            events.append(event)

        elif roll < 0.135:
            gain = random.randint(2, max(3, int(math.sqrt(state["population"]) + 2)))
            state["population"] += gain
            state["morale"] = clamp(state["morale"] + random.uniform(2, 6))
            event = self._add_event(
                state,
                "migration",
                f"A band of travelers chose to stay. The population grew by {gain}.",
            )
            events.append(event)

        elif roll < 0.165:
            gain = random.uniform(3, 7)
            state["knowledge"] = clamp(state["knowledge"] + gain)
            event = self._add_event(
                state,
                "discovery",
                "A practical breakthrough changed how people work, build, and teach.",
                major=state["knowledge"] >= 60,
                notify=False,
            )
            events.append(event)

        elif roll < 0.195:
            state["stability"] = clamp(state["stability"] + random.uniform(4, 9))
            state["morale"] = clamp(state["morale"] + random.uniform(4, 8))
            event = self._add_event(
                state,
                "festival",
                "The settlement held a festival that would be remembered for generations.",
            )
            events.append(event)

        elif roll < 0.215:
            damage = random.uniform(5, 12)
            state["stability"] = clamp(state["stability"] - damage)
            state["morale"] = clamp(state["morale"] - random.uniform(2, 6))
            event = self._add_event(
                state,
                "fire",
                "A night fire destroyed homes and workshops before the bucket lines contained it.",
                major=state["stability"] < 30,
                notify=state["stability"] < 30,
            )
            events.append(event)

        # Milestones guarantee that history never becomes completely silent.
        if state["year"] % 25 == 0:
            event = self._add_event(
                state,
                "milestone",
                f"{state['name']} reached Year {state['year']} with a population of {state['population']}.",
                major=True,
                notify=True,
            )
            events.append(event)

        # A civilization can come frighteningly close to collapse, but V1 always leaves an ember.
        if state["population"] <= 2 and (
            state["food"] < 18 or state["health"] < 18 or state["stability"] < 18
        ):
            state["food"] = max(state["food"], 35)
            state["health"] = max(state["health"], 35)
            state["stability"] = max(state["stability"], 35)
            event = self._add_event(
                state,
                "last_hearth",
                "Only a final hearth remained. Against absurd odds, it endured and began rebuilding.",
                major=True,
                notify=True,
            )
            events.append(event)

        return events

    def advance_to_now(self) -> list[dict[str, Any]]:
        with self._lock:
            now = utc_now()
            last = parse_iso(self.state["last_simulated_at"])
            elapsed_seconds = max(0, (now - last).total_seconds())
            years_due = int(elapsed_seconds // YEAR_SECONDS)

            if years_due <= 0:
                return []

            # Defensive cap for a corrupt timestamp. 10,000 years is plenty of apocalypse.
            years_due = min(years_due, 10_000)
            generated: list[dict[str, Any]] = []

            for _ in range(years_due):
                generated.extend(self._year_tick(self.state))

            simulated_until = last.timestamp() + (years_due * YEAR_SECONDS)
            self.state["last_simulated_at"] = iso(
                datetime.fromtimestamp(simulated_until, tz=timezone.utc)
            )
            self._save()
            return generated

    def public_state(self) -> dict[str, Any]:
        with self._lock:
            self.advance_to_now()
            s = self.state
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
                "chronicle": list(reversed(s["chronicle"][-12:])),
            }

    def visit(self) -> dict[str, Any]:
        with self._lock:
            self.advance_to_now()
            current_year = self.state["year"]
            last_year = self.state.get("last_visit_year", 0)
            unseen = [
                e for e in self.state["chronicle"] if e["year"] > last_year
            ]

            if last_year == 0:
                report = {
                    "years_away": 0,
                    "headline": f"You arrive in Year {current_year}.",
                    "events": unseen[-8:],
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
                }

            self.state["last_visit_year"] = current_year
            self.state["last_visit_at"] = iso(utc_now())
            self._save()

            return {
                "report": report,
                "state": self.public_state(),
            }

    def nuke(self) -> dict[str, Any]:
        with self._lock:
            self.state = self._new_state()
            self._save()
            return self.public_state()
