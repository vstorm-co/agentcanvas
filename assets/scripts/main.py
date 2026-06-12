"""Pydantic AI V2 (v2.0.0b7) demo: a thinking agent, a nested sub-agent exposed as a
tool, five tools and a multi-turn conversation — all traced to Logfire.

Run:  uv run --prerelease=allow python main.py

Requires in .env:
  - OPENROUTER_API_KEY   (your OpenRouter key)
  - LOGFIRE_WRITE_TOKEN  (telemetry is sent to Logfire)
"""

from __future__ import annotations

import os
import random
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import logfire
from dotenv import load_dotenv
from pydantic_ai import Agent, RunContext
from pydantic_ai.capabilities import Thinking
from pydantic_ai.models.openrouter import OpenRouterModel

load_dotenv(Path(__file__).resolve().parents[2] / ".env")
logfire.configure(token=os.environ["LOGFIRE_WRITE_TOKEN"], service_name="pydantic-ai-demo")
logfire.instrument_pydantic_ai()


@dataclass
class UserDeps:
    name: str
    age: int


model = OpenRouterModel("openai/gpt-5.5")

# A nested sub-agent with its own tools, reached through the main agent's plan_trip
# tool — this is how agents compose and grow.
trip_planner = Agent(
    model,
    capabilities=[Thinking(effort="medium")],
    name="trip_planner",
    instructions=(
        "You are a local trip planner. Think step by step about the weather and the "
        "user's options, then propose a concrete plan. Reply in English."
    ),
)


@trip_planner.tool_plain
def get_weather(city: str) -> str:
    """Return the (simulated) current weather for a given city."""
    conditions = ["sunny", "cloudy", "rainy", "snowy", "foggy"]
    return f"In {city}: {random.choice(conditions)}, {random.randint(-5, 30)}°C."


@trip_planner.tool_plain
def list_attractions(city: str) -> list[str]:
    """List a few notable attractions in the given city."""
    catalog = {
        "krakow": ["Wawel Castle", "Main Market Square", "Kazimierz district"],
        "default": ["Old Town", "City Museum", "Riverside Park"],
    }
    return catalog.get(city.lower(), catalog["default"])


# The main agent: thinking enabled via a capability, five tools, one of which
# delegates to the trip_planner sub-agent.
agent = Agent(
    model,
    deps_type=UserDeps,
    capabilities=[Thinking(effort="medium")],
    name="assistant",
    instructions=(
        "You are a friendly assistant. Think briefly about what the user needs, then "
        "use your tools to answer concretely. When a question is about visiting a city, "
        "delegate to the plan_trip tool. Reply in English."
    ),
)


@agent.tool
def get_user_profile(ctx: RunContext[UserDeps]) -> str:
    """Return the current user's name and age."""
    return f"The user's name is {ctx.deps.name} and they are {ctx.deps.age} years old."


@agent.tool
def calculate_birth_year(ctx: RunContext[UserDeps]) -> int:
    """Estimate the user's birth year from their age."""
    return datetime.now().year - ctx.deps.age


@agent.tool
def recommend_activity(ctx: RunContext[UserDeps]) -> str:
    """Recommend an activity tailored to the user's age."""
    age = ctx.deps.age
    if age < 18:
        return "Playing football or board games with friends."
    if age < 60:
        return "Running, climbing, or an evening with a good book."
    return "A walk in the park and a game of chess."


@agent.tool_plain
def roll_dice(sides: int = 6) -> int:
    """Roll a die with the given number of sides and return the result."""
    return random.randint(1, sides)


@agent.tool
async def plan_trip(ctx: RunContext[UserDeps], city: str) -> str:
    """Delegate to the trip-planner sub-agent to build a day plan for a city."""
    result = await trip_planner.run(
        f"Plan a great day in {city}. Check the weather and suggest attractions."
    )
    return result.output


def main() -> None:
    deps = UserDeps(name="Kacper", age=28)

    # A multi-turn conversation captured under one Logfire trace.
    with logfire.span("conversation"):
        turn1 = agent.run_sync(
            "Hi! Introduce me — my name, age and birth year — then roll a six-sided die.",
            deps=deps,
        )
        print("\n=== Turn 1 ===\n" + turn1.output)

        turn2 = agent.run_sync(
            "Thanks! Now I'm thinking of visiting Krakow tomorrow. "
            "Plan my day there and recommend an activity that fits my age.",
            deps=deps,
            message_history=turn1.all_messages(),
        )
        print("\n=== Turn 2 ===\n" + turn2.output)


if __name__ == "__main__":
    main()
