"""Draw a pastel "yarn basket" SVG from a GitHub user's contribution calendar.

One yarn ball per week. Busier weeks roll bigger yarn balls; quiet weeks
leave a tiny dot. A little black cat walks across the floor. No numbers
are drawn anywhere.

Usage:
  GITHUB_TOKEN=... python garden.py <username> <out.svg>      # live data (GitHub Actions)
  python garden.py --levels sample_levels.txt <out.svg>        # offline preview
"""

import json
import os
import sys
import urllib.request

LEVEL = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2,
         "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}

YARN = ["#f9a8d4", "#c4b5fd", "#a5d8ff", "#fbcfe8", "#ddd6fe", "#f0abfc"]
CAT = "#161418"

W, H = 860, 170
FLOOR = 140


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


def tier(score: int) -> int:
    """Weekly score (sum of daily levels, 0-28) -> yarn size tier 0-4."""
    if score == 0:
        return 0
    return 1 if score <= 3 else 2 if score <= 8 else 3 if score <= 15 else 4


def yarn_ball(x: float, t: int, color: str) -> str:
    if t == 0:
        return f'<circle cx="{x:.1f}" cy="{FLOOR - 1.2}" r="1.2" fill="#e9d5e6"/>'
    r = 3 + t * 3.4
    cy = FLOOR - r
    parts = [f'<circle cx="{x:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{color}"/>']
    for k in range(3):
        off = (k - 1) * r * 0.45
        parts.append(f'<path d="M{x - r * 0.8:.1f} {cy + off - r * 0.2:.1f} Q{x:.1f} {cy + off - r * 0.6:.1f} '
                     f'{x + r * 0.8:.1f} {cy + off + r * 0.2:.1f}" stroke="#ffffff" stroke-width="1" '
                     f'fill="none" opacity="0.8"/>')
    if t >= 3:  # a loose strand on the busiest weeks
        parts.append(f'<path d="M{x + r:.1f} {FLOOR - 1} q8 -2 14 1 t12 -1" stroke="{color}" '
                     f'stroke-width="1.2" fill="none"/>')
    return "".join(parts)


def leg(x: float, phase: int) -> str:
    return (f'<g><rect x="{x - 2.2}" y="-3" width="4.4" height="7" rx="2.2" fill="{CAT}"/>'
            f'<animateTransform attributeName="transform" type="rotate" '
            f'values="{12 * phase} {x} -3;{-12 * phase} {x} -3;{12 * phase} {x} -3" '
            f'dur="0.8s" repeatCount="indefinite"/></g>')


def black_cat() -> str:
    """Black cat walking right with its face toward the viewer. Origin = paws on the floor."""
    tail_path = "M-14 -12 C-28 -12 -31 -30 -23 -36 C-18 -40 -13 -36 -16 -32"
    tail = (f'<g><path d="{tail_path}" stroke="{CAT}" stroke-width="6" fill="none" stroke-linecap="round"/>'
            '<animateTransform attributeName="transform" type="rotate" '
            'values="0 -15 -12;-8 -15 -12;0 -15 -12" dur="1.6s" repeatCount="indefinite"/></g>')
    torso = (f'<path d="M-18 -7 C-19 -17 -8 -21 3 -20 C13 -19 18 -14 18 -8 C18 -3 14 0 9 0 '
             f'L-13 0 C-17 0 -18 -3 -18 -7 Z" fill="{CAT}"/>')
    ears = (f'<path d="M6 -28 Q6 -40 9.5 -41 Q12 -40 16 -34.5 Z" fill="{CAT}"/>'
            f'<path d="M18 -34.5 Q22 -40 24.5 -41 Q28 -40 28 -28 Z" fill="{CAT}"/>')
    head = f'<ellipse cx="17" cy="-25.5" rx="13" ry="11" fill="{CAT}"/>'
    eyes = "".join(
        f'<circle cx="{ex}" cy="-27.5" r="2.9" fill="#ffffff" stroke="#f3e3a0" stroke-width="0.8"/>'
        f'<circle cx="{ex + 0.45}" cy="-27.45" r="2.35" fill="{CAT}"/>'
        f'<circle cx="{ex + 1.2}" cy="-28.4" r="0.75" fill="#ffffff"/>'
        for ex in (13.4, 20.6))
    bob = ('<animateTransform attributeName="transform" type="translate" '
           'values="0 0;0 -1.2;0 0" dur="0.4s" repeatCount="indefinite"/>')
    return (f'<g>{tail}{leg(-11, 1)}{leg(-6, -1)}{torso}{leg(7, -1)}{leg(12, 1)}'
            f'<g><g transform="translate(-2.5 3)">{ears}{head}{eyes}</g>{bob}</g></g>')


def render(weeks: list[int]) -> str:
    n = len(weeks)
    step = (W - 40) / max(n, 1)
    balls = "".join(yarn_ball(20 + i * step + step / 2, tier(s), YARN[i % len(YARN)])
                    for i, s in enumerate(weeks))
    y = FLOOR - 3
    walker = (f'<g transform="translate(-50 {y})"><g transform="scale(1.15)">{black_cat()}</g>'
              f'<animateTransform attributeName="transform" type="translate" '
              f'values="-50 {y};{W + 50} {y}" dur="40s" repeatCount="indefinite"/></g>')
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
        f'role="img" aria-label="yarn basket: one yarn ball per week">'
        f'<clipPath id="frame"><rect width="{W}" height="{H}" rx="16"/></clipPath>'
        f'<g clip-path="url(#frame)">'
        f'<rect width="{W}" height="{H}" fill="#fff7fb"/>'
        f'<rect y="{FLOOR}" width="{W}" height="{H - FLOOR}" fill="#f1e6f0"/>'
        f'{balls}{walker}</g></svg>'
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
