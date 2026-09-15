"""Guard the committed R8 evidence bundle.

docs/evidence/model-comparison-2026-09-15/ holds sanitised copies of raw traces so a
clean clone can inspect and regenerate the Groq-hosted rows of MODEL_COMPARISON.md
without artifacts/. These tests protect the two properties that matter: the bundle
stays free of the Groq organization id, and the manifest stays an accurate index of
what is actually on disk.
"""
import json
import re
from pathlib import Path

from scripts.model_scoreboard import collect_records

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "docs/evidence/model-comparison-2026-09-15"
TRACES = BUNDLE / "traces"
MANIFEST = BUNDLE / "manifest.json"

ORG_ID_PATTERN = re.compile(r"org_[0-9a-zA-Z]{10,}")


def test_bundle_exists():
    assert BUNDLE.is_dir()
    assert TRACES.is_dir()
    assert MANIFEST.is_file()


def test_no_organization_id_anywhere_in_the_bundle():
    offenders = []
    for path in BUNDLE.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if ORG_ID_PATTERN.search(text):
            offenders.append(str(path.relative_to(BUNDLE)))
    assert offenders == [], f"organization id leaked into: {offenders}"


def test_manifest_run_count_matches_run_list():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["run_count"] == len(manifest["runs"])
    assert sum(manifest["eligibility_counts"].values()) == manifest["run_count"]


def test_every_manifest_entry_points_at_a_real_sanitized_file():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for run in manifest["runs"]:
        bundle_file = BUNDLE / run["bundle_path"]
        assert bundle_file.is_file(), f"missing {run['bundle_path']}"
        assert run["bundle_path"].startswith("traces/")


def test_every_traced_file_is_indexed_in_the_manifest():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    indexed = {(BUNDLE / run["bundle_path"]).resolve() for run in manifest["runs"]}
    on_disk = {p.resolve() for p in TRACES.rglob("*.jsonl")}
    assert on_disk == indexed


def test_sanitized_runs_are_the_ones_flagged_infra_admission_failure():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    sanitized = {run["bundle_path"] for run in manifest["runs"] if run["sanitized"]}
    assert len(sanitized) == manifest["sanitization"]["files_sanitized_in_bundle"]
    for run in manifest["runs"]:
        if run["sanitized"]:
            assert run["eligibility"] == "infra_admission_failure"


def test_scoreboard_reads_the_bundle_with_no_exclusions():
    records, exclusions = collect_records(TRACES)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert exclusions == []
    assert len(records) == manifest["run_count"]


def test_bundle_is_self_contained_no_artifacts_reference_required():
    # The whole point of R8: a clean clone reads this bundle, not a user's local
    # artifacts/. Every path recorded for scoreboard consumption must live under the
    # bundle itself.
    for path in TRACES.rglob("*.jsonl"):
        assert "artifacts" not in path.relative_to(TRACES).parts
