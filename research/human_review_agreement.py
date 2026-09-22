from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from research.human_review_integration import (
    HUMAN_TO_DATASET_LABEL,
    LABEL_MAPPING_VERSION,
    NOT_COMPARABLE,
    RAW_REVIEWER01_SHA256,
    RAW_REVIEWER02_SHA256,
    REVIEW_ID_POLICY_VERSION,
    load_and_validate_reviewer01_archive,
    load_and_validate_reviewer02_archive,
    map_human_label,
    write_reviewer02_derived_layer,
)


AGREEMENT_SCHEMA_VERSION = "driftwatch-human-human-agreement-v1"
REVIEWER02_PROVENANCE_STATUS = "FIRST_COMPLETED_AUTHORITATIVE_BLIND_RETURN"


class HumanReviewAgreementError(ValueError):
    """Raised when genuine human-review agreement cannot be calculated safely."""


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def compare_case_sets(
    reviewer01_bundle: Mapping[str, Any],
    reviewer02_bundle: Mapping[str, Any],
    holdout_ids: Iterable[str],
) -> dict[str, Any]:
    reviewer01_ids = {record["record_id"] for record in reviewer01_bundle["records"]}
    reviewer02_ids = {record["record_id"] for record in reviewer02_bundle["records"]}
    common_ids = reviewer01_ids & reviewer02_ids
    union_ids = reviewer01_ids | reviewer02_ids
    holdout_overlap = union_ids & set(holdout_ids)
    return {
        "reviewer01_count": len(reviewer01_ids),
        "reviewer02_count": len(reviewer02_ids),
        "common_record_count": len(common_ids),
        "missing_from_reviewer02": sorted(reviewer01_ids - reviewer02_ids),
        "extra_in_reviewer02": sorted(reviewer02_ids - reviewer01_ids),
        "external_holdout_overlap": sorted(holdout_overlap),
        "case_sets_identical": reviewer01_ids == reviewer02_ids,
    }


def cohens_kappa(label_pairs: Sequence[tuple[str, str]]) -> dict[str, Any]:
    comparable_pairs = [
        (left, right)
        for left, right in label_pairs
        if left != NOT_COMPARABLE and right != NOT_COMPARABLE
    ]
    count = len(comparable_pairs)
    if not count:
        return {
            "status": "NOT_AVAILABLE",
            "reason": "No comparable label pairs are available.",
            "comparable_count": 0,
            "observed_agreement": None,
            "expected_agreement": None,
            "cohens_kappa": None,
        }

    left_counts = Counter(left for left, _ in comparable_pairs)
    right_counts = Counter(right for _, right in comparable_pairs)
    observed = sum(left == right for left, right in comparable_pairs) / count
    categories = sorted(set(left_counts) | set(right_counts))
    expected = sum(
        (left_counts[category] / count) * (right_counts[category] / count)
        for category in categories
    )
    if expected == 1.0:
        return {
            "status": "NOT_AVAILABLE_DEGENERATE_MARGINALS",
            "reason": "Expected agreement is 1.0, so the kappa denominator is zero.",
            "comparable_count": count,
            "observed_agreement": observed,
            "expected_agreement": expected,
            "cohens_kappa": None,
            "reviewer01_marginals": dict(sorted(left_counts.items())),
            "reviewer02_marginals": dict(sorted(right_counts.items())),
        }

    value = (observed - expected) / (1.0 - expected)
    return {
        "status": "AVAILABLE_UNWEIGHTED",
        "method": "Cohen's kappa, unweighted nominal categories",
        "formula": "(observed_agreement - expected_agreement) / (1 - expected_agreement)",
        "comparable_count": count,
        "observed_agreement": observed,
        "expected_agreement": expected,
        "cohens_kappa": value,
        "reviewer01_marginals": dict(sorted(left_counts.items())),
        "reviewer02_marginals": dict(sorted(right_counts.items())),
        "limitations": [
            "The sample contains only 14 scoped cases.",
            "Kappa is sensitive to concentrated and imbalanced category marginals.",
            "The estimate is descriptive for this review package and is not an accuracy measure.",
            "No weighted kappa is used because the label ontology has no governed ordinal scale.",
        ],
    }


def _rationale_reference(bundle: Mapping[str, Any], record: Mapping[str, Any]) -> dict[str, str]:
    return {
        "raw_source_sha256": bundle["raw_source_sha256"],
        "raw_submission_entry_name": record["raw_submission_entry_name"],
        "derived_review_id": record["derived_review_id"],
        "json_pointer": "/rationale",
    }


def build_agreement_analysis(
    reviewer01_bundle: Mapping[str, Any],
    reviewer02_bundle: Mapping[str, Any],
    holdout_ids: Iterable[str],
) -> dict[str, Any]:
    case_set = compare_case_sets(reviewer01_bundle, reviewer02_bundle, holdout_ids)
    if not case_set["case_sets_identical"]:
        raise HumanReviewAgreementError(f"reviewer case sets differ: {case_set}")
    if case_set["external_holdout_overlap"]:
        raise HumanReviewAgreementError(
            f"protected external-holdout overlap detected: {case_set['external_holdout_overlap']}"
        )

    reviewer01_by_id = {record["record_id"]: record for record in reviewer01_bundle["records"]}
    reviewer02_by_id = {record["record_id"]: record for record in reviewer02_bundle["records"]}
    rows: list[dict[str, Any]] = []
    for record_id in sorted(reviewer01_by_id):
        reviewer01_record = reviewer01_by_id[record_id]
        reviewer02_record = reviewer02_by_id[record_id]
        reviewer01 = reviewer01_record["submission"]
        reviewer02 = reviewer02_record["submission"]
        reviewer01_mapped = map_human_label(reviewer01["independent_label"])
        reviewer02_mapped = map_human_label(reviewer02["independent_label"])
        comparable = NOT_COMPARABLE not in {reviewer01_mapped, reviewer02_mapped}
        exact_match = reviewer01_mapped == reviewer02_mapped if comparable else None
        rows.append(
            {
                "record_id": record_id,
                "reviewer01_original_label": reviewer01["independent_label"],
                "reviewer01_mapped_label": reviewer01_mapped,
                "reviewer01_confidence": reviewer01["confidence"],
                "reviewer02_original_label": reviewer02["independent_label"],
                "reviewer02_mapped_label": reviewer02_mapped,
                "reviewer02_confidence": reviewer02["confidence"],
                "comparable": comparable,
                "exact_match": exact_match,
                "disagreement": (not exact_match) if comparable else None,
                "confidence_pair": f"{reviewer01['confidence']}|{reviewer02['confidence']}",
                "notes": (
                    "exact mapped-label agreement"
                    if exact_match is True
                    else "mapped labels differ; pending adjudication"
                    if exact_match is False
                    else "excluded from agreement denominator by versioned mapping"
                ),
                "reviewer01_rationale_reference": _rationale_reference(
                    reviewer01_bundle, reviewer01_record
                ),
                "reviewer02_rationale_reference": _rationale_reference(
                    reviewer02_bundle, reviewer02_record
                ),
            }
        )

    comparable_rows = [row for row in rows if row["comparable"]]
    exact_count = sum(row["exact_match"] is True for row in comparable_rows)
    disagreements = [row for row in comparable_rows if row["disagreement"] is True]
    mapped_categories = list(dict.fromkeys(HUMAN_TO_DATASET_LABEL.values()))
    cross_tab = {
        reviewer01_label: {
            reviewer02_label: sum(
                row["reviewer01_mapped_label"] == reviewer01_label
                and row["reviewer02_mapped_label"] == reviewer02_label
                for row in comparable_rows
            )
            for reviewer02_label in mapped_categories
        }
        for reviewer01_label in mapped_categories
    }
    kappa = cohens_kappa(
        [
            (row["reviewer01_mapped_label"], row["reviewer02_mapped_label"])
            for row in rows
        ]
    )

    confidence_pairs: dict[str, dict[str, Any]] = {}
    for confidence_pair in sorted({row["confidence_pair"] for row in comparable_rows}):
        pair_rows = [row for row in comparable_rows if row["confidence_pair"] == confidence_pair]
        pair_exact = sum(row["exact_match"] is True for row in pair_rows)
        confidence_pairs[confidence_pair] = {
            "case_count": len(pair_rows),
            "exact_agreement_count": pair_exact,
            "exact_agreement_rate": pair_exact / len(pair_rows),
            "interpretation_limit": (
                "Descriptive only; confidence is not probability and small pair counts do not support inference."
            ),
        }

    confidence_summary = {
        "schema_version": AGREEMENT_SCHEMA_VERSION,
        "reviewer01_confidence_distribution": dict(
            sorted(Counter(row["reviewer01_confidence"] for row in rows).items())
        ),
        "reviewer02_confidence_distribution": dict(
            sorted(Counter(row["reviewer02_confidence"] for row in rows).items())
        ),
        "agreement_by_confidence_pair": confidence_pairs,
        "confidence_is_probability": False,
        "confidence_used_to_overwrite_labels": False,
    }
    agreement_summary = {
        "schema_version": AGREEMENT_SCHEMA_VERSION,
        "mapping_version": LABEL_MAPPING_VERSION,
        "review_id_policy_version": REVIEW_ID_POLICY_VERSION,
        "case_set": case_set,
        "total_common_cases": case_set["common_record_count"],
        "comparable_cases": len(comparable_rows),
        "not_comparable_cases": len(rows) - len(comparable_rows),
        "exact_agreements": exact_count,
        "disagreements": len(disagreements),
        "percent_exact_agreement": (
            100.0 * exact_count / len(comparable_rows) if comparable_rows else None
        ),
        "mapped_label_cross_tabulation": {
            "row_dimension": "reviewer01_mapped_label",
            "column_dimension": "reviewer02_mapped_label",
            "categories": mapped_categories,
            "matrix": cross_tab,
        },
        "cohens_kappa": kappa,
        "methodological_status": (
            "Genuine human-human agreement for two documented independent blind reviewers; "
            "descriptive for the scoped case set, not ground-truth accuracy or adjudication."
        ),
    }
    disagreement_rows = [
        {
            "record_id": row["record_id"],
            "reviewer01_label": row["reviewer01_original_label"],
            "reviewer01_confidence": row["reviewer01_confidence"],
            "reviewer02_label": row["reviewer02_original_label"],
            "reviewer02_confidence": row["reviewer02_confidence"],
            "reviewer01_rationale_reference": row["reviewer01_rationale_reference"],
            "reviewer02_rationale_reference": row["reviewer02_rationale_reference"],
        }
        for row in disagreements
    ]
    return {
        "case_set": case_set,
        "agreement_summary": agreement_summary,
        "comparison_rows": rows,
        "disagreement_rows": disagreement_rows,
        "confidence_summary": confidence_summary,
    }


def write_agreement_artifacts(
    analysis: Mapping[str, Any],
    output_root: str | Path,
    *,
    reviewer01_bundle: Mapping[str, Any],
    reviewer02_bundle: Mapping[str, Any],
) -> dict[str, Any]:
    output = Path(output_root)
    output.mkdir(parents=True, exist_ok=False)
    _write_json(output / "agreement_summary.json", analysis["agreement_summary"])
    _write_json(
        output / "comparison_table.json",
        {
            "schema_version": AGREEMENT_SCHEMA_VERSION,
            "mapping_version": LABEL_MAPPING_VERSION,
            "record_count": len(analysis["comparison_rows"]),
            "records": analysis["comparison_rows"],
        },
    )
    _write_json(
        output / "disagreements.json",
        {
            "schema_version": AGREEMENT_SCHEMA_VERSION,
            "status": "PENDING_GOVERNED_ADJUDICATION",
            "record_count": len(analysis["disagreement_rows"]),
            "records": analysis["disagreement_rows"],
            "adjudication_performed": False,
        },
    )
    _write_json(output / "confidence_summary.json", analysis["confidence_summary"])
    _write_json(
        output / "provenance.json",
        {
            "schema_version": AGREEMENT_SCHEMA_VERSION,
            "reviewer01_raw_source_sha256": reviewer01_bundle["raw_source_sha256"],
            "reviewer02_raw_source_sha256": reviewer02_bundle["raw_source_sha256"],
            "reviewer02_authoritative_return_status": REVIEWER02_PROVENANCE_STATUS,
            "reviewer02_independence_basis": (
                "Reviewer 02 explicitly confirmed the first completed return contains genuine "
                "initial independent judgements based only on supplied blind evidence."
            ),
            "reviewer02_timestamp_quality": "PLACEHOLDER_CONFIRMED",
            "later_reviewer02_attempts": "NON_AUTHORITATIVE_EXCLUDED_FROM_ANALYSIS",
            "mapping_version": LABEL_MAPPING_VERSION,
            "simulated_reviewer_material_used": False,
            "provisional_dataset_labels_used": False,
            "raw_sources_modified": False,
        },
    )
    disagreement_ids = [row["record_id"] for row in analysis["disagreement_rows"]]
    _write_json(
        output / "adjudication_plan.json",
        {
            "schema_version": AGREEMENT_SCHEMA_VERSION,
            "status": "PROPOSED_NOT_EXECUTED",
            "gold_set_status": (
                "READY FOR GOVERNED ADJUDICATION"
                if disagreement_ids
                else "PARTIALLY SATISFIED"
            ),
            "adjudication_candidate_count": len(disagreement_ids),
            "adjudication_candidate_record_ids": disagreement_ids,
            "evidence_to_supply": [
                "the original blind packet for the version pair",
                "both immutable reviewer labels, confidence values, rationales, and evidence references",
                "source-entry hashes and derived review identifiers",
                "the governed label definitions and evidence hierarchy",
            ],
            "visibility_proposal": (
                "Keep personal reviewer identities masked. Have the adjudicator record an initial "
                "packet-only assessment before revealing the de-identified Reviewer 01 and Reviewer 02 "
                "labels and rationales for reconciliation. The current guide does not otherwise define "
                "adjudicator blinding."
            ),
            "preservation": (
                "Store the adjudicated label, rationale, evidence references, adjudicator identifier, "
                "timestamp, and policy version as a new linked record; never replace either original review."
            ),
            "simulated_material_allowed": False,
            "adjudication_performed": False,
            "label_promotion_performed": False,
        },
    )
    return {
        "output_root": str(output),
        "artifact_count": 6,
        "disagreement_count": len(disagreement_ids),
    }


def _load_holdout_ids(path: str | Path) -> list[str]:
    with Path(path).open(encoding="utf-8") as handle:
        payload = json.load(handle)
    return [row["record_id"] for row in payload.get("records", [])]


def run_phase5c(
    *,
    reviewer01_zip: str | Path,
    reviewer02_zip: str | Path,
    reviewer02_packet_root: str | Path,
    holdout_manifest: str | Path,
    reviewer02_output: str | Path,
    agreement_output: str | Path,
) -> dict[str, Any]:
    reviewer01_bundle = load_and_validate_reviewer01_archive(
        reviewer01_zip, expected_sha256=RAW_REVIEWER01_SHA256
    )
    reviewer02_bundle = load_and_validate_reviewer02_archive(
        reviewer02_zip,
        packet_root=reviewer02_packet_root,
        expected_sha256=RAW_REVIEWER02_SHA256,
    )
    holdout_ids = _load_holdout_ids(holdout_manifest)
    analysis = build_agreement_analysis(reviewer01_bundle, reviewer02_bundle, holdout_ids)
    reviewer02_validation = write_reviewer02_derived_layer(
        reviewer02_bundle, reviewer02_output
    )
    agreement_artifacts = write_agreement_artifacts(
        analysis,
        agreement_output,
        reviewer01_bundle=reviewer01_bundle,
        reviewer02_bundle=reviewer02_bundle,
    )
    return {
        "reviewer02_validation": reviewer02_validation,
        "agreement_summary": analysis["agreement_summary"],
        "agreement_artifacts": agreement_artifacts,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate authoritative Reviewer 02 evidence and derive genuine human-human agreement."
    )
    parser.add_argument(
        "--reviewer01-zip",
        default="DriftWatch_Human_Review_Raw_Return_Reviewer01_2026-09-22.zip",
    )
    parser.add_argument(
        "--reviewer02-zip",
        default="DriftWatch_Human_Review_Raw_Return_Reviewer02_2026-09-22.zip",
    )
    parser.add_argument("--reviewer02-packet-root", default="reviewer_human_02/packets")
    parser.add_argument(
        "--holdout-manifest",
        default="artifacts/driftbench/phase3h/external_holdout_manifest.json",
    )
    parser.add_argument(
        "--reviewer02-output",
        default="artifacts/human_review/reviewer02/authoritative_return",
    )
    parser.add_argument(
        "--agreement-output",
        default="artifacts/human_review/agreement/reviewer01_vs_reviewer02",
    )
    args = parser.parse_args()
    result = run_phase5c(
        reviewer01_zip=args.reviewer01_zip,
        reviewer02_zip=args.reviewer02_zip,
        reviewer02_packet_root=args.reviewer02_packet_root,
        holdout_manifest=args.holdout_manifest,
        reviewer02_output=args.reviewer02_output,
        agreement_output=args.agreement_output,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
