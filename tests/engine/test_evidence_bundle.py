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

from scripts.evidence_bundle import (QUALITY_EXCLUDED_LABELS, classify_eligibility, content_sha256,
                                     recompute_bundle_report)
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


# --- A4: manifest eligibility must be reproducible from trace content, not hand-typed ---

def test_manifest_eligibility_is_reproducible_from_each_traces_own_content():
    """This is the test that must fail if someone hand-edits a label in manifest.json
    without the trace changing, or if a trace changes without the manifest being
    regenerated. Recomputes classify_eligibility() straight from each trace file on
    disk and compares against what the manifest claims for that same file.
    """
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    checked = 0
    for run in manifest["runs"]:
        path = BUNDLE / run["bundle_path"]
        text = path.read_text(encoding="utf-8")
        row = None
        for line in text.splitlines():
            if not line.strip():
                continue
            candidate = json.loads(line)
            if isinstance(candidate, dict) and candidate.get("type") == "run_metadata":
                row = candidate
                break
        assert row is not None, f"no run_metadata row in {run['bundle_path']}"
        label, basis = classify_eligibility(row)
        assert label == run["eligibility"], (
            f"{run['bundle_path']}: manifest says {run['eligibility']!r}, "
            f"recomputed from the trace says {label!r} ({basis})")
        assert basis == run["eligibility_basis"]
        checked += 1
    assert checked == manifest["run_count"]


def test_manifest_trace_hash_matches_recomputed_content_hash():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for run in manifest["runs"]:
        path = BUNDLE / run["bundle_path"]
        assert content_sha256(path) == run["trace_sha256_in_bundle"], run["bundle_path"]


def test_recompute_bundle_report_matches_manifest_run_count_and_counts():
    report = recompute_bundle_report(BUNDLE)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert report["run_count"] == manifest["run_count"]
    assert report["eligibility_counts"] == manifest["eligibility_counts"]


def test_legacy_infra_failure_unspecified_label_is_gone():
    # The review found this label overstated the evidence (no captured status/body
    # does not prove the request never reached the model). It must not reappear.
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    labels = {run["eligibility"] for run in manifest["runs"]}
    assert "infra_failure_unspecified" not in labels
    assert "undetermined_failure" in labels


def test_eligibility_counts_sum_to_run_count_and_every_label_is_placed_in_exactly_one_denominator():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    counts = manifest["eligibility_counts"]
    assert sum(counts.values()) == manifest["run_count"]
    quality_total = sum(n for label, n in counts.items() if label not in QUALITY_EXCLUDED_LABELS)
    quality_pass = counts.get("scored_pass", 0)
    assert quality_total == 46
    assert quality_pass == 43
    # generated-output failures and unresolved timeouts must stay counted, not dropped
    assert counts.get("scored_fail_generated_output", 0) == 1
    assert counts.get("timeout_undetermined_cause", 0) == 1
    assert counts.get("undetermined_failure", 0) == 1


def test_scoreboard_quality_pass_rate_over_the_bundle_is_43_of_46_not_43_of_57():
    records, exclusions = collect_records(TRACES)
    assert exclusions == []
    non_ablated = [r for r in records if not r["ablated"]]
    assert len(non_ablated) == 57
    quality_scored = [r for r in non_ablated
                      if r["oracle"] is not None and r["eligibility"] not in QUALITY_EXCLUDED_LABELS]
    assert len(quality_scored) == 46
    assert sum(1 for r in quality_scored if r["oracle"]) == 43
