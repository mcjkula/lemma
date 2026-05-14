"""Training JSONL export payloads."""

from pathlib import Path

from lemma.lean.proof_metrics import LeanProofMetrics
from lemma.protocol import LemmaChallenge
from lemma.validator.training_export import append_epoch_jsonl, round_summary_record, training_record


def test_training_record_roundtrip_fields(tmp_path: Path) -> None:
    resp = LemmaChallenge(
        theorem_id="x",
        theorem_statement="theorem p : True := by sorry",
        imports=["Mathlib"],
        lean_toolchain="t",
        mathlib_rev="m",
        deadline_unix=0,
        metronome_id="z",
        proof_script="namespace Submission\n",
        model_card="prover=openai model=demo base_url=https://example.invalid/v1",
    )
    proof_metrics = LeanProofMetrics(
        proof_declaration_bytes=538,
        proof_declaration_lines=9,
        probe_exit_code=0,
        proof_declaration_delimiters=21,
        proof_declaration_max_depth=5,
    )
    export_context = {
        "lemma_version": "0.1.0",
        "generated_registry_sha256": "c" * 64,
    }
    row = training_record(
        block=42,
        theorem_id="tid",
        uid=7,
        resp=resp,
        proof_metrics=proof_metrics,
        coldkey="coldkey-public",
        export_context=export_context,
    )
    assert row["schema_version"] == 3
    assert row["export_profile"] == "full"
    assert row["uid"] == 7
    assert row["coldkey"] == "coldkey-public"
    assert row["export_context"] == export_context
    assert row["theorem_id"] == "tid"
    assert row["theorem_statement"] == "theorem p : True := by sorry"
    assert "rubric" not in row
    assert row["proof_metrics"]["proof_declaration_bytes"] == 538

    out = tmp_path / "train.jsonl"
    append_epoch_jsonl(out, [row], {7: 0.25})
    line = out.read_text(encoding="utf-8").strip()
    assert '"validator_weight": 0.25' in line


def test_training_record_summary_no_scores(tmp_path: Path) -> None:
    resp = LemmaChallenge(
        theorem_id="x",
        theorem_statement="theorem p : True := by sorry",
        imports=["Mathlib"],
        lean_toolchain="t",
        mathlib_rev="m",
        deadline_unix=0,
        metronome_id="z",
        proof_script="namespace Submission\n",
        model_card="m",
    )
    row = training_record(
        block=1,
        theorem_id="tid",
        uid=3,
        resp=resp,
        profile="summary",
        export_context={"lemma_version": "0.1.0"},
    )
    assert row["schema_version"] == 2
    assert row["export_profile"] == "summary"
    assert "proof_script" not in row

    out = tmp_path / "r.jsonl"
    append_epoch_jsonl(out, [row], {3: 0.5}, include_weights=False)
    line = out.read_text(encoding="utf-8").strip()
    assert "validator_weight" not in line


def test_round_summary_record_exports_zero_pass_round(tmp_path: Path) -> None:
    row = round_summary_record(
        block=10,
        theorem_id="gen/10",
        passed_uids=set(),
        export_context={"lemma_version": "0.1.0"},
    )
    assert row["passed_uids"] == []

    out = tmp_path / "summary.jsonl"
    append_epoch_jsonl(out, [row], {3: 0.5})
    line = out.read_text(encoding="utf-8").strip()
    assert "validator_weight" not in line


def test_round_summary_record_can_export_rolling_scores() -> None:
    row = round_summary_record(
        block=10,
        theorem_id="gen/10",
        passed_uids={2},
        rolling_score_by_uid={2: 0.4, 3: 0.2},
        weight_by_uid={2: 0.8, 3: 0.2},
    )

    assert row["rolling_score_by_uid"] == {"2": 0.4, "3": 0.2}
    assert row["weight_by_uid"] == {"2": 0.8, "3": 0.2}
