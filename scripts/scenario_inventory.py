"""Inventory the scenario corpus from the files themselves.

File count is not coverage. Two files that drive the same tools through the same
workflow are one workflow measured twice. This reports what is actually distinct.

    python scripts/scenario_inventory.py --write docs/SCENARIO_INVENTORY.md
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Development exposure: fixtures the engine has been tuned against are no longer unseen.
EXPOSURE = {"dev": "development", "live_dev": "development", "planner_probes": "held out, never run"}
PLANNED = {"text": 30, "audio": 18, "visual": 12}


def display_path(path):
    """Render `path` relative to ROOT, or as an absolute path when it lies outside ROOT.

    Mirrors `display_path` in `scripts/model_scoreboard.py` so both tools report
    out-of-tree paths the same way instead of raising.
    """
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def scenarios(root):
    root = root.resolve()
    for path in sorted(root.rglob("*.json")):
        try:
            definition = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        events = definition.get("events") or []
        if not events or events[0].get("kind") != "session_start":
            continue
        tools = tuple(sorted(t["name"] for t in events[0].get("payload", {}).get("tools", [])))
        inputs = [e for e in events[1:] if e.get("kind") in {"transcript", "audio", "frame"}]
        modalities = sorted({e["kind"] for e in inputs}) or ["none"]
        yield {
            "set": path.parent.name,
            "path": display_path(path),
            "id": definition.get("id", path.stem),
            "tools": tools,
            "modalities": modalities,
            "turns": len(inputs),
            "faults": sorted(k for k, v in (definition.get("environment") or {}).items()
                             if isinstance(v, dict) and any(
                                 v.get(f) for f in ("lost_response", "fail_before_commit",
                                                    "commit_then_unknown"))),
        }


def render(rows):
    by_tools = defaultdict(list)
    for row in rows:
        by_tools[row["tools"]].append(row)
    modality_counts = defaultdict(int)
    for row in rows:
        for modality in row["modalities"]:
            modality_counts[modality] += 1

    out = [f"Generated from {len(rows)} scenario files.",
           "Regenerate with `python scripts/scenario_inventory.py --write docs/SCENARIO_INVENTORY.md`.",
           "", "## Coverage against the plan", "",
           "| Modality | Planned | Present |", "|---|---|---|",
           f"| text (`transcript`) | {PLANNED['text']} | {modality_counts.get('transcript', 0)} |",
           f"| audio (`audio`) | {PLANNED['audio']} | {modality_counts.get('audio', 0)} |",
           f"| visual (`frame`) | {PLANNED['visual']} | {modality_counts.get('frame', 0)} |",
           "", f"Distinct tool sets: **{len(by_tools)}** across {len(rows)} files. "
           f"Longest scenario: **{max(r['turns'] for r in rows)}** user turns.", "",
           "## Every scenario", "",
           "| Set | Scenario | Turns | Modalities | Faults | Exposure |", "|---|---|---|---|---|---|"]
    for row in rows:
        out.append(f"| {row['set']} | `{row['id']}` | {row['turns']} | {', '.join(row['modalities'])} | "
                   f"{', '.join(row['faults']) or '-'} | {EXPOSURE.get(row['set'], 'unlabelled')} |")
    out += ["", "## Workflows measured more than once", "",
            "Each group drives the same tool set. A group of more than one is one workflow "
            "measured repeatedly, not independent coverage.", "",
            "| Tool set | Files |", "|---|---|"]
    for tools, group in sorted(by_tools.items(), key=lambda item: -len(item[1])):
        out.append(f"| {', '.join(tools) or 'none'} | {len(group)}: " +
                   ", ".join(f"`{r['id']}`" for r in group) + " |")
    return "\n".join(out) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenarios", default=str(ROOT / "scenarios"))
    parser.add_argument("--write")
    args = parser.parse_args()
    rows = list(scenarios(Path(args.scenarios)))
    body = render(rows)
    if args.write:
        target = Path(args.write)
        header = target.read_text(encoding="utf-8").split("<!-- generated -->")[0] if target.exists() else ""
        target.write_text(header + "<!-- generated -->\n" + body, encoding="utf-8")
        print(f"wrote {target}")
    else:
        print(body)


if __name__ == "__main__":
    main()
