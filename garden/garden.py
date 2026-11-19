"""Draw a pastel "commit garden" SVG from a GitHub user's contribution calendar.

One plant per week. Busier weeks grow taller, bigger flowers; quiet weeks
stay as little grass tufts. No numbers are drawn anywhere.

Usage:
  GITHUB_TOKEN=... python garden.py <username> <out.svg>      # live data (GitHub Actions)
  python garden.py --levels sample_levels.txt <out.svg>        # offline preview
"""

import json
import os
import random
import sys
import urllib.request

LEVEL = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2,
         "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}

PETALS = ["#f9a8d4", "#c4b5fd", "#a5d8ff", "#fbcfe8", "#ddd6fe", "#f0abfc"]
STEM = "#86b86b"
LEAF = "#a7d38b"
GRASS = "#c7e3b0"
CENTER = "#fde68a"

W, H = 860, 170
GROUND = 140


def fetch_weeks(user: str, token: str) -> list[int]:
    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar { weeks { contributionDays { contributionLevel } } }
        }
      }
    }"""
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": {"login": user}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        data = json.load(resp)
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return [sum(LEVEL[d["contributionLevel"]] for d in w["contributionDays"]) for w in weeks]


def weeks_from_levels_file(path: str) -> list[int]:
    digits = open(path).read().split()[-1]
    days = [int(c) for c in digits]
    return [sum(days[i:i + 7]) for i in range(0, len(days), 7)]


def grass(x: float, rng: random.Random) -> str:
    blades = []
    for dx in (-3, 0, 3):
        h = rng.uniform(4, 10)
        lean = rng.uniform(-2.5, 2.5)
        blades.append(
            f'<path d="M{x + dx:.1f} {GROUND} q{lean:.1f} {-h * 0.6:.1f} {lean * 1.6:.1f} {-h:.1f}" '
            f'stroke="{GRASS}" stroke-width="1.6" fill="none" stroke-linecap="round"/>')
    return "".join(blades)


def flower(x: float, score: int, rng: random.Random, i: int) -> str:
    # score: weekly sum of daily levels (0-28) -> plant size tier
    if score == 0:
        return grass(x, rng)
    tier = 1 if score <= 3 else 2 if score <= 8 else 3 if score <= 15 else 4
    height = 14 + tier * 20 + rng.uniform(-3, 3)
    top = GROUND - height
    color = PETALS[i % len(PETALS)]
    parts = [grass(x, rng)]
    stem = (f'<line x1="{x:.1f}" y1="{GROUND}" x2="{x:.1f}" y2="{top:.1f}" '
            f'stroke="{STEM}" stroke-width="2" stroke-linecap="round"/>')
    leaf_y = GROUND - height * 0.45
    leaf = (f'<ellipse cx="{x + 5:.1f}" cy="{leaf_y:.1f}" rx="5" ry="2.4" fill="{LEAF}" '
            f'transform="rotate(-25 {x + 5:.1f} {leaf_y:.1f})"/>')
    if tier == 1:
        head = (f'<ellipse cx="{x - 3:.1f}" cy="{top:.1f}" rx="4" ry="2.2" fill="{LEAF}"/>'
                f'<ellipse cx="{x + 3:.1f}" cy="{top:.1f}" rx="4" ry="2.2" fill="{LEAF}"/>')
    else:
        r = 2.5 + tier * 1.6
        n = 5 if tier < 4 else 6
        petals = "".join(
            f'<ellipse cx="{x:.1f}" cy="{top - r * 0.75:.1f}" rx="{r * 0.55:.1f}" ry="{r * 0.85:.1f}" '
            f'fill="{color}" transform="rotate({k * 360 / n:.0f} {x:.1f} {top:.1f})"/>'
            for k in range(n)
        )
        head = petals + f'<circle cx="{x:.1f}" cy="{top:.1f}" r="{r * 0.45:.1f}" fill="{CENTER}"/>'
    sway = rng.choice([2, 3, 4])
    dur = rng.uniform(3.5, 5.5)
    anim = (f'<animateTransform attributeName="transform" type="rotate" '
            f'values="-{sway} {x:.1f} {GROUND};{sway} {x:.1f} {GROUND};-{sway} {x:.1f} {GROUND}" '
            f'dur="{dur:.1f}s" repeatCount="indefinite"/>')
    parts.append(f"<g>{stem}{leaf if tier > 1 else ''}{head}{anim}</g>")
    return "".join(parts)


def butterfly(x: float, y: float) -> str:
    return (f'<g opacity="0.9"><ellipse cx="{x - 4}" cy="{y}" rx="4" ry="3" fill="#ddd6fe"/>'
            f'<ellipse cx="{x + 4}" cy="{y}" rx="4" ry="3" fill="#fbcfe8"/>'
            f'<line x1="{x}" y1="{y - 3}" x2="{x}" y2="{y + 3}" stroke="#8b7aa8" stroke-width="1.2"/>'
            f'<animateTransform attributeName="transform" type="translate" '
            f'values="0 0; -14 -6; -4 4; 0 0" dur="7s" repeatCount="indefinite"/></g>')


def render(weeks: list[int]) -> str:
    rng = random.Random(42)
    n = len(weeks)
    step = (W - 40) / max(n, 1)
    plants = "".join(flower(20 + i * step + step / 2, s, rng, i) for i, s in enumerate(weeks))
    best = max(range(n), key=lambda i: weeks[i]) if n else 0
    bx = 20 + best * step + step / 2
    extra = butterfly(max(40, bx - 34), 48) if n and weeks[best] > 0 else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
        f'role="img" aria-label="commit garden: one flower per week">'
        f'<rect x="0" y="0" width="{W}" height="{H}" rx="16" fill="#fff7fb"/>'
        f'<rect x="0" y="{GROUND}" width="{W}" height="{H - GROUND}" rx="0" fill="#f3e8d8"/>'
        f'<rect x="0" y="{GROUND}" width="{W}" height="4" fill="#e6d5bf"/>'
        f"{plants}{extra}</svg>"
    )


def main() -> None:
    args = sys.argv[1:]
    if args and args[0] == "--levels":
        weeks, out = weeks_from_levels_file(args[1]), args[2]
    else:
        user, out = args[0], args[1]
        weeks = fetch_weeks(user, os.environ["GITHUB_TOKEN"])
    with open(out, "w") as f:
        f.write(render(weeks))


if __name__ == "__main__":
    main()
