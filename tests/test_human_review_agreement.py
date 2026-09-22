from __future__ import annotations

from research.human_review_agreement import (
    build_agreement_analysis,
    cohens_kappa,
    compare_case_sets,
)
from research.human_review_integration import (
    INITIAL_BLIND,
    NOT_COMPARABLE,
    REVIEWER01_ID,
    REVIEWER02_ID,
    derive_review_id,
)


def _record(record_id: str, reviewer_id: str, label: str, confidence: str) -> dict:
    return {
        "record_id": record_id,
        "derived_review_id": derive_review_id(reviewer_id, record_id, INITIAL_BLIND),
        "raw_submission_entry_name": f"submissions/{record_id}.json",
        "submission": {
            "record_id": record_id,
            "reviewer_id": reviewer_id,
            "review_round": INITIAL_BLIND,
            "independent_label": label,
            "confidence": confidence,
            "rationale": f"Rationale for {record_id}",
        },
    }


def _bundle(reviewer_id: str, labels: list[str]) -> dict:
    return {
        "raw_source_sha256": reviewer_id.upper(),
        "records": [
            _record(
                f"record_{index}",
                reviewer_id,
                label,
                "HIGH" if index == 0 else "MEDIUM",
            )
            for index, label in enumerate(labels)
        ],
    }


def test_case_set_identity_reports_missing_extra_and_holdout_overlap():
    reviewer01 = _bundle(REVIEWER01_ID, ["UNCERTAIN", "RISKY_TRANSITION"])
    reviewer02 = _bundle(REVIEWER02_ID, ["UNCERTAIN", "RISKY_TRANSITION"])

    report = compare_case_sets(reviewer01, reviewer02, ["record_99"])

    assert report["case_sets_identical"] is True
    assert report["common_record_count"] == 2
    assert report["missing_from_reviewer02"] == []
    assert report["extra_in_reviewer02"] == []
    assert report["external_holdout_overlap"] == []


def test_exact_agreement_disagreement_extraction_and_confidence_pairs():
    reviewer01 = _bundle(
        REVIEWER01_ID,
        ["UNCERTAIN", "RISKY_TRANSITION", "RISKY_TRANSITION"],
    )
    reviewer02 = _bundle(
        REVIEWER02_ID,
        ["UNCERTAIN", "UNCERTAIN", "RISKY_TRANSITION"],
    )

    analysis = build_agreement_analysis(reviewer01, reviewer02, [])

    assert analysis["agreement_summary"]["exact_agreements"] == 2
    assert analysis["agreement_summary"]["disagreements"] == 1
    assert [row["record_id"] for row in analysis["disagreement_rows"]] == ["record_1"]
    assert analysis["comparison_rows"][0]["confidence_pair"] == "HIGH|HIGH"
    assert analysis["disagreement_rows"][0]["reviewer01_rationale_reference"]["json_pointer"] == "/rationale"


def test_unweighted_cohens_kappa_is_transparent_and_excludes_not_comparable():
    result = cohens_kappa(
        [
            ("uncertain", "uncertain"),
            ("uncertain", "risky_transition"),
            ("risky_transition", "risky_transition"),
            ("risky_transition", "risky_transition"),
            (NOT_COMPARABLE, "uncertain"),
        ]
    )

    assert result["status"] == "AVAILABLE_UNWEIGHTED"
    assert result["comparable_count"] == 4
    assert result["observed_agreement"] == 0.75
    assert result["expected_agreement"] == 0.5
    assert result["cohens_kappa"] == 0.5


def test_cohens_kappa_reports_degenerate_marginals_without_inventing_value():
    result = cohens_kappa([("uncertain", "uncertain"), ("uncertain", "uncertain")])

    assert result["status"] == "NOT_AVAILABLE_DEGENERATE_MARGINALS"
    assert result["cohens_kappa"] is None
